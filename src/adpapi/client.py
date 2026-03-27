"""ADP API client for interacting with the ADP Workforce Now API.

This module provides the AdpApiClient class for authenticating with and making
requests to the ADP Workforce Now API using OAuth 2.0 client credentials flow
with certificate-based authentication.
"""

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from adpapi.odata_filters import FilterExpression
from adpapi.sessions import ApiSession, RequestMethod
from adpapi.utils import (
    resolve_path_parameter_sets,
    substitute_path_parameters,
    validate_path_parameters,
)

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 30
TOKEN_BUFFER_SECONDS = 300  # Refresh token 5 minutes before expiration


CERT_DEFAULT = "certificate.pem"
KEY_DEFAULT = "adp.key"


@dataclass
class AdpCredentials:
    """Container for ADP API authentication credentials.

    Holds the OAuth 2.0 client credentials and paths to the mTLS certificate
    and private key required for ADP API authentication.

    Attributes:
        client_id: OAuth 2.0 client ID from ADP
        client_secret: OAuth 2.0 client secret from ADP
        cert_path: Path to the mTLS certificate file (.pem). Defaults to 'certificate.pem'
        key_path: Path to the private key file. Defaults to 'adp.key'

    Example:
        >>> credentials = AdpCredentials(
        ...     client_id="my_client_id",
        ...     client_secret="my_secret",
        ...     cert_path="/path/to/cert.pem",
        ...     key_path="/path/to/key.key"
        ... )
    """

    client_id: str
    client_secret: str
    cert_path: str | None = CERT_DEFAULT
    key_path: str | None = KEY_DEFAULT

    @staticmethod
    def from_env() -> "AdpCredentials":
        """Load credentials from environment variables.

        Reads authentication credentials from the following environment variables:
        - CLIENT_ID (required): OAuth 2.0 client ID
        - CLIENT_SECRET (required): OAuth 2.0 client secret
        - CERT_PATH (optional): Path to mTLS certificate, defaults to 'certificate.pem'
        - KEY_PATH (optional): Path to private key, defaults to 'adp.key'

        Returns:
            AdpCredentials instance populated from environment variables

        Raises:
            ValueError: If CLIENT_ID or CLIENT_SECRET are not set

        Example:
            >>> from dotenv import load_dotenv
            >>> load_dotenv()
            >>> credentials = AdpCredentials.from_env()
        """
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")

        # Read optional mTLS certificate/key paths (defaults assume files in project root).
        cert_path = os.getenv("CERT_PATH")
        key_path = os.getenv("KEY_PATH")

        if cert_path is None:
            logger.warning(
                f"No environment variables found for CERT_PATH, defaulting to {CERT_DEFAULT}"
            )

        if key_path is None:
            logger.warning(
                f"No environment variables found for KEY_PATH, defaulting to {KEY_DEFAULT}"
            )

        if client_id is None or client_secret is None:
            raise ValueError("CLIENT_ID and CLIENT_SECRET environment variables must be set")

        return AdpCredentials(client_id, client_secret, cert_path, key_path)


class AdpApiClient:
    """Client for interacting with the ADP Workforce Now API.

    Handles OAuth 2.0 authentication with certificate-based mutual TLS,
    automatic token refresh, and provides methods for calling both paginated
    OData endpoints and direct REST endpoints with path parameters.

    The client is designed to be used as a context manager to ensure proper
    cleanup of HTTP sessions.

    Example:
        >>> from adpapi import AdpApiClient, AdpCredentials
        >>> credentials = AdpCredentials.from_env()
        >>> with AdpApiClient(credentials) as client:
        ...     workers = client.call_endpoint("/hr/v2/workers")
    """

    def __init__(self, credentials: AdpCredentials, retry_on_statuses: list | None = None):
        """Initialize the ADP API client.

        Args:
            credentials: AdpCredentials object containing client_id, client_secret,
                and paths to certificate and key files
            retry_on_statuses: List of HTTP status codes that should trigger automatic
                retries with exponential backoff. If None, defaults to [429, 500, 502, 503, 504].
                Pass an empty list [] to disable retries entirely.

        Raises:
            ValueError: If certificate path or key path is None
            FileNotFoundError: If certificate or key file does not exist at the specified path

        Example:
            >>> credentials = AdpCredentials.from_env()
            >>> # Default retry behavior
            >>> client = AdpApiClient(credentials)
            >>>
            >>> # Custom retry statuses
            >>> client = AdpApiClient(credentials, retry_on_statuses=[429, 503])
            >>>
            >>> # Disable retries
            >>> client = AdpApiClient(credentials, retry_on_statuses=[])
        """
        if credentials.cert_path is None or credentials.key_path is None:
            raise ValueError("Certificate path and key path must not be None")
        if not os.path.exists(credentials.cert_path) or not os.path.exists(credentials.key_path):
            logger.error("Missing Certificate or Key File.")
            raise FileNotFoundError("Certificate or key file not found.")

        self.client_id = credentials.client_id
        self.client_secret = credentials.client_secret
        self.cert_path = credentials.cert_path
        self.key_path = credentials.key_path
        self.cert = (self.cert_path, self.key_path)
        self.session = requests.Session()
        self._setup_retry_strategy(status_forcelist=retry_on_statuses)

        # Token expiration tracking
        self.token: str | None = None
        self.token_expires_at = 0

    @property
    def payload(self) -> dict[str, str]:
        return {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

    @property
    def base_url(self) -> str:
        return "https://api.adp.com"

    def _setup_retry_strategy(
        self, retries: int = 3, backoff_factor: float = 0.5, status_forcelist: list | None = None
    ):
        """Configure retry strategy with exponential backoff for HTTP requests."""
        if status_forcelist is None:
            # Default sensible foreclist
            status_forcelist = [429, 500, 502, 503, 504]
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        logger.debug(f"Retry strategy configured: {retries} retries with {backoff_factor}s backoff")

    def _is_token_expired(self) -> bool:
        """Check if token is expired or will expire soon."""
        return time.time() >= self.token_expires_at - TOKEN_BUFFER_SECONDS

    def _get_token(self, timeout: int = DEFAULT_TIMEOUT) -> str:
        logger.debug("Requesting Token from ADP Accounts endpoint")
        TOKEN_URL = "https://accounts.adp.com/auth/oauth/v2/token"
        try:
            response = self.session.post(
                TOKEN_URL,
                data=self.payload,
                cert=self.cert,
                timeout=timeout,
            )
            response.raise_for_status()
            token_json = response.json()
            token = token_json.get("access_token")
            if not token:
                raise ValueError("No access token in response")

            # Track token expiration
            expires_in = token_json.get("expires_in", 3600)  # Default 1 hour
            self.token_expires_at = time.time() + expires_in
            logger.info(f"Token Acquired (expires in {expires_in}s)")
            return token
        except requests.RequestException as e:
            logger.error(f"Token request failed: {e}")
            raise

    def _ensure_valid_token(self, timeout: int = DEFAULT_TIMEOUT):
        """Refresh token if expired."""
        if self.token is None or self._is_token_expired():
            logger.debug("Token expired, refreshing...")
            self.token = self._get_token(timeout)

    def _get_headers(self, masked: bool = True) -> dict[str, str]:
        """Build request headers with Bearer token and masking preference."""
        # * May need to be tweaked in the future if OData calls or other forms are needed. Not necessary for MVP
        accept = "application/json"
        if not masked:
            accept += ";masked=false"
            logging.debug(f"Calling _get_headers with accept = {accept}")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": accept,
        }

        return headers

    def get_masked_headers(self) -> dict[str, str]:
        """Get HTTP headers with masked=true (hides PII).

        Returns:
            Dictionary of HTTP headers with Authorization and Accept headers,
            where Accept is set to request masked data.
        """
        return self._get_headers(True)

    def get_unmasked_headers(self) -> dict[str, str]:
        """Get HTTP headers with masked=false (shows PII if permitted).

        Returns:
            Dictionary of HTTP headers with Authorization and Accept headers,
            where Accept is set to request unmasked data.

        Note:
            Access to unmasked data is subject to tenant permissions.
        """
        return self._get_headers(False)

    def _handle_filters(self, filters: str | FilterExpression | None = None) -> str:
        """Convert filter input (string or FilterExpression) to OData string.

        Args:
            filters: Filter as string or FilterExpression object, or None

        Returns:
            OData filter string, or empty string if no filters
        """
        if filters is None:
            return ""
        elif isinstance(filters, str):
            try:
                filters = FilterExpression.from_string(filters)
            except ValueError:
                logger.error(f"Error parsing filter expression: {filters}")
                raise

        # Remove outer parentheses added by BinaryOp if present
        odata_str = filters.to_odata()
        if odata_str.startswith("(") and odata_str.endswith(")"):
            odata_str = odata_str[1:-1]
        return odata_str

    def _resolve_method(self, method: str | RequestMethod) -> RequestMethod:
        """Normalize method input into a RequestMethod enum value."""
        if isinstance(method, RequestMethod):
            return method

        try:
            return RequestMethod(method.upper())
        except ValueError as e:
            raise ValueError(f"Unsupported request method: {method}") from e

    def _build_query_params(
        self,
        params: dict[str, Any] | None = None,
        select: list[str] | None = None,
        filters: str | FilterExpression | None = None,
    ) -> dict[str, Any]:
        """Build query params, including optional OData select/filter clauses."""
        query_params: dict[str, Any] = dict(params) if params else {}

        if select:
            select_param = ",".join(select)
            logging.debug(f"Restricting OData Selection to {select_param}")
            query_params["$select"] = select_param

        filter_param = self._handle_filters(filters)
        if filter_param:
            logging.debug(f"Filtering Results according to OData query: {filter_param}")
            query_params["$filter"] = filter_param

        return query_params

    def _build_call_session(
        self,
        masked: bool,
        timeout: int,
        params: dict[str, Any] | None = None,
    ) -> ApiSession:
        """Create a configured ApiSession for endpoint calls."""
        get_headers_fn = self.get_masked_headers if masked else self.get_unmasked_headers
        call_session = ApiSession(self.session, self.cert, get_headers_fn, timeout=timeout)
        if params:
            call_session.set_params(params)
        return call_session

    @staticmethod
    def _parse_json_response(response: requests.Response) -> dict:
        """Parse JSON response body and surface decode errors with context."""
        try:
            return response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise

    def _clean_endpoint(self, endpoint: str) -> str:
        starts_with_base = endpoint.startswith(self.base_url)
        starts_with_path = endpoint.startswith("/")

        if not (starts_with_base or starts_with_path):
            logger.error(f"Incorrect Endpoint Received {endpoint}")
            raise ValueError(
                f"Incorrect Endpoint Received: {endpoint}. Endpoints must either start with `/` or with {self.base_url}."
            )

        if starts_with_base:
            endpoint = endpoint.split(self.base_url)[1]
            logger.warning(
                "Full URL Specification not needed, prefer to use the endpoint string.\n"
                f"(Ex: Prefer {endpoint} over {self.base_url}{endpoint})."
            )

        return endpoint.strip()

    def call_endpoint(
        self,
        endpoint: str,
        select: list[str] | None = None,
        filters: str | FilterExpression | None = None,
        masked: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
        page_size: int = 100,
        max_requests: int | None = None,
        method: str = "GET",
    ) -> list[dict]:
        """Call a paginated OData endpoint with automatic pagination handling.

        Use this method for list/search operations that return multiple records.
        The client automatically handles pagination by incrementing $skip until
        the API returns HTTP 204 (No Content) or max_requests is reached.

        Args:
            endpoint: API endpoint path (e.g., '/hr/v2/workers'). Can optionally include
                the full URL, but path-only is preferred.
            select: List of OData columns to retrieve. Uses dot notation in Python
                (e.g., 'workers/person/legalName') which is converted to OData's
                forward-slash notation. If None, all columns are returned.
            filters: OData filter expression as a string or FilterExpression object.
                Use FilterExpression for type-safe filter building.
            masked: Whether to request masked data (hides PII). Set to False to request
                unmasked data if your tenant permissions allow it. Defaults to True.
            timeout: Request timeout in seconds. Defaults to 30.
            page_size: Number of records per request (max 100). Defaults to 100.
            max_requests: Maximum number of paginated requests to make. Useful for
                testing or limiting data pulls. If None, fetches all available records.
            method: HTTP method to use. Defaults to 'GET'. Non-GET methods will only
                make a single request (no pagination).

        Returns:
            List of dictionaries, where each dictionary is a response from the API.
            For paginated GET requests, this will contain one dict per page.

        Raises:
            ValueError: If endpoint format is invalid (must start with '/' or base URL)
            requests.RequestException: If the HTTP request fails
            json.JSONDecodeError: If the response body is not valid JSON

        Example:
            >>> # Basic usage
            >>> workers = client.call_endpoint("/hr/v2/workers")
            >>>
            >>> # With column selection
            >>> workers = client.call_endpoint(
            ...     "/hr/v2/workers",
            ...     select=["workers/person/legalName", "workers/associateOID"]
            ... )
            >>>
            >>> # With filtering
            >>> from adpapi import FilterExpression
            >>> active = FilterExpression.field("workers/status").eq("Active")
            >>> workers = client.call_endpoint("/hr/v2/workers", filters=active)
            >>>
            >>> # Limited fetch for testing
            >>> workers = client.call_endpoint("/hr/v2/workers", max_requests=2)
        """

        # Request Cleanup and Validation Logic
        if page_size > 100:
            logger.warning("Page size > 100 not supported by API endpoint. Limiting to 100.")
            page_size = 100

        # Output/Request Initialization
        endpoint = self._clean_endpoint(endpoint)
        url = self.base_url + endpoint
        request_method = self._resolve_method(method)

        query_params = self._build_query_params(select=select, filters=filters)
        output = []
        skip = 0

        call_session = self._build_call_session(masked=masked, timeout=timeout)

        if request_method == RequestMethod.GET:
            query_params["$top"] = page_size
        elif max_requests is not None and max_requests > 1:
            logger.warning(
                "max_requests > 1 was provided for a non-GET request; only one request will be made."
            )

        while True:
            params = dict(query_params)
            if request_method == RequestMethod.GET:
                params["$skip"] = skip

            call_session.set_params(params)
            self._ensure_valid_token(timeout)
            response = call_session._request(url, method=request_method)

            if request_method == RequestMethod.GET and response.status_code == 204:
                logger.debug("End of pagination reached (204 No Content)")
                break

            # json.JSONDecodeError handling is centralized in _parse_json_response.
            data = self._parse_json_response(response)
            output.append(data)

            if request_method != RequestMethod.GET:
                break

            if max_requests is not None and len(output) >= max_requests:
                logger.debug(f"Max Requests reached: {max_requests}")
                break
            skip += page_size

        return output

    def call_rest_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        masked: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
        params: dict | None = None,
        select: list[str] | None = None,
        filters: str | FilterExpression | None = None,
        max_workers: int = 1,
        inject_path_params: bool = False,
        **kwargs: Any,
    ) -> list[dict]:
        """Call a REST endpoint with path parameter substitution and optional parallelization.

        Use this method for direct resource lookups when you already know the resource
        identifier(s). Supports batch fetching multiple resources and parallel execution
        for improved throughput.

        Args:
            endpoint: API endpoint path template with placeholders in curly braces
                (e.g., '/hr/v2/workers/{associateOID}').
            method: HTTP method to use. Defaults to 'GET'.
            masked: Whether to request masked data (hides PII). Set to False to request
                unmasked data if your tenant permissions allow it. Defaults to True.
            timeout: Request timeout in seconds. Defaults to 30.
            params: Additional query parameters to include in the request.
            select: List of OData columns to retrieve. Works the same as in call_endpoint().
            filters: OData filter expression as a string or FilterExpression object.
            max_workers: Number of threads for parallel requests. Use 1 for sequential
                (default). Recommended range is 5-10 for parallel execution.
            inject_path_params: When True, the resolved path parameters are merged into
                each response dictionary. Useful when the API response doesn't include
                the requested identifier (e.g., associate OIDs). Defaults to False.
            **kwargs: Path parameters to substitute into the endpoint template.
                - Single values: workerId='123' → '/hr/v2/workers/123'
                - Lists: workerId=['123', '456'] → multiple requests for each ID
                - Multiple params: workerId='123', jobId='J1' → '/hr/v2/workers/123/jobs/J1'

        Returns:
            List of dictionaries, one for each resolved endpoint URL. For batch requests
            with lists, returns one response per list item.

        Raises:
            ValueError: If required path parameters are missing from kwargs, or if endpoint
                format is invalid.
            requests.RequestException: If the HTTP request fails.
            json.JSONDecodeError: If the response body is not valid JSON.

        Example:
            >>> # Single resource fetch
            >>> worker = client.call_rest_endpoint(
            ...     "/hr/v2/workers/{associateOID}",
            ...     associateOID="G3349PRDL000001"
            ... )
            >>>
            >>> # Batch fetch (sequential)
            >>> workers = client.call_rest_endpoint(
            ...     "/hr/v2/workers/{associateOID}",
            ...     associateOID=["G3349PRDL000001", "G3349PRDL000002"]
            ... )
            >>>
            >>> # Parallel batch fetch (5-10x faster)
            >>> workers = client.call_rest_endpoint(
            ...     "/hr/v2/workers/{associateOID}",
            ...     max_workers=10,
            ...     associateOID=list_of_50_ids
            ... )
            >>>
            >>> # With column selection and ID injection
            >>> workers = client.call_rest_endpoint(
            ...     "/hr/v2/workers/{associateOID}",
            ...     select=["workers/person/legalName"],
            ...     inject_path_params=True,
            ...     associateOID=["G3349PRDL000001", "G3349PRDL000002"]
            ... )
            >>> # Each response now includes: {"associateOID": "G3349PRDL000001", ...}
            >>>
            >>> # Multiple path parameters
            >>> job = client.call_rest_endpoint(
            ...     "/hr/v2/workers/{associateOID}/jobs/{jobId}",
            ...     associateOID="G3349PRDL000001",
            ...     jobId="J42"
            ... )
        """
        endpoint = self._clean_endpoint(endpoint)
        is_valid, missing_params = validate_path_parameters(endpoint, kwargs)
        if not is_valid:
            raise ValueError(f"Missing required path parameters: {', '.join(missing_params)}")

        urls = substitute_path_parameters(endpoint, kwargs)
        if not urls:
            return []

        request_method = self._resolve_method(method)
        query_params = self._build_query_params(params=params, select=select, filters=filters)
        call_session = self._build_call_session(masked=masked, timeout=timeout, params=query_params)

        # Ensure a valid token once before all requests to avoid race conditions
        # with concurrent threads each trying to refresh the token simultaneously.
        self._ensure_valid_token(timeout)

        def _fetch(url: str) -> dict:
            full_url = self.base_url + url
            response = call_session._request(url=full_url, method=request_method)
            return self._parse_json_response(response)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            output = list(executor.map(_fetch, urls))

        if inject_path_params:
            param_sets = resolve_path_parameter_sets(endpoint, kwargs)
            for response, param_set in zip(output, param_sets, strict=False):
                response.update(param_set)

        return output

    def __enter__(self):
        """Context manager entry.

        Returns:
            Self, allowing the client to be used in a with statement.

        Example:
            >>> with AdpApiClient(credentials) as client:
            ...     workers = client.call_endpoint("/hr/v2/workers")
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup session.

        Closes the underlying HTTP session to release resources.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Returns:
            False to propagate any exception that occurred
        """
        self.session.close()
        logger.debug("Session closed")
        return False
