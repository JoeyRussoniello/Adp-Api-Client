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
from adpapi.utils import substitute_path_parameters, validate_path_parameters

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 30
TOKEN_BUFFER_SECONDS = 300  # Refresh token 5 minutes before expiration


CERT_DEFAULT = "certificate.pem"
KEY_DEFAULT = "adp.key"


@dataclass(frozen=True)
class AdpCredentials:
    client_id: str
    client_secret: str
    cert_path: str | None = CERT_DEFAULT
    key_path: str | None = KEY_DEFAULT

    @staticmethod
    def from_env() -> "AdpCredentials":
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

        return AdpCredentials(client_id, client_secret)


class AdpApiClient:
    def __init__(self, credentials: AdpCredentials):
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
        self._setup_retry_strategy()

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

    def _setup_retry_strategy(self, retries: int = 3, backoff_factor: float = 0.5):
        """Configure retry strategy with exponential backoff for HTTP requests."""
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
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
        return self._get_headers(True)

    def get_unmasked_headers(self) -> dict[str, str]:
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

    def _clean_endpoint(self, endpoint: str) -> str:
        starts_with_base = endpoint.startswith(self.base_url)
        starts_with_path = endpoint.startswith("/")

        if not (starts_with_base or starts_with_path):
            logger.error(f"Incorrect Endpoint Received {endpoint}")
            raise ValueError(f"Incorrect Endpoint Received: {endpoint}")

        if starts_with_base:
            endpoint = endpoint.split(self.base_url)[1]
            logger.warning(
                "Full URL Specification not needed, prefer to use the endpoint string.\n"
                f"(Ex: Prefer {endpoint} over {self.base_url}{endpoint})."
            )

        return endpoint

    def call_endpoint(
        self,
        endpoint: str,
        select: list[str] | None = None,
        filters: str | FilterExpression | None = None,
        masked: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
        page_size: int = 100,
        max_requests: int | None = None,
    ) -> list[dict]:
        """Call any Registered ADP Endpoint

        Args:
            endpoint (str): API Endpoint or qualified URL to call
            select (List[str]): Table Columns to pull
            masked (bool, optional): Mask Sensitive Columns Containing Personally Identifiable Information. Defaults to True.
            filters (str | FilterExpression, optional): OData Filter Expression. Strings will be passed directly,
                or OData strings can be automatically created from `adpapi.odata_filters.FilterExpression` objects
            timeout (int, optional): Time to wait on. Defaults to 30.
            page_size (int, optional): Amount of records to pull per API call (max 100). Defaults to 100.
            max_requests (Optional[int], optional): Maximum number of requests to make (for quick testing). Defaults to None.

        Raises:
            ValueError: When given an endpoint not following the call convention

        Returns:
            List[Dict]: The collection of API responses
        """

        # Request Cleanup and Validation Logic
        if page_size > 100:
            logger.warning("Page size > 100 not supported by API endpoint. Limiting to 100.")
            page_size = 100

        # Output/Request Initialization
        endpoint = self._clean_endpoint(endpoint)
        url = self.base_url + endpoint
        filter_param = self._handle_filters(filters)
        # Populate here instead of mutable default arguments
        if select is None:
            select = []
        select_param = ",".join(select)
        output = []
        skip = 0

        get_headers_fn = self.get_masked_headers if masked else self.get_unmasked_headers

        call_session = ApiSession(self.session, self.cert, get_headers_fn, timeout=timeout)

        params: dict[str, Any] = {"$top": page_size}
        if select_param:
            logging.debug(f"Restricting OData Selection to {select_param}")
            params["$select"] = select_param
        if filter_param:
            logging.debug(f"Filtering Results according to OData query: {filter_param}")
            params["$filter"] = filter_param

        while True:
            params["$skip"] = skip
            call_session.set_params(params)
            self._ensure_valid_token(timeout)
            response = call_session.get(url)

            if response.status_code == 204:
                logger.debug("End of pagination reached (204 No Content)")
                break

            try:
                data = response.json()
                output.append(data)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise

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
        max_workers: int = 1,
        **kwargs,
    ) -> list[dict]:
        """Call a RestAPI Endpoint

        Args:
            endpoint (str): the endpoint path template (e.g. '/hr/workers/{workerId}')
            method (Optional[str], optional): the HTTP method to use for the request. Defaults to 'GET'.
            masked (Optional[bool], optional): whether to use masked headers. Defaults to True.
            timeout (Optional[int], optional): the request timeout in seconds. Defaults to DEFAULT_TIMEOUT.
            params (Optional[dict], optional): query parameters for the request. Defaults to None.
            max_workers (int, optional): maximum number of threads for parallel requests. Defaults to 1 (sequential).
            **kwargs: path parameters to substitute into the endpoint template (e.g workerId=['123', '456']) - can be single values or lists of values for batch requests
        Raises:
            ValueError: if required path parameters are missing or if endpoint format is incorrect

        Returns:
            List[Dict]: the collection of API responses for each substituted endpoint
        """
        is_valid, missing_params = validate_path_parameters(endpoint, kwargs)
        if not is_valid:
            raise ValueError(f"Missing required path parameters: {', '.join(missing_params)}")

        urls = substitute_path_parameters(endpoint, kwargs)
        if not urls:
            return []

        # Establish the call session
        get_headers_fn = self.get_masked_headers if masked else self.get_unmasked_headers

        call_session = ApiSession(self.session, self.cert, get_headers_fn, timeout=timeout)
        if params:
            call_session.set_params(params)

        # Ensure a valid token once before all requests to avoid race conditions
        # with concurrent threads each trying to refresh the token simultaneously.
        self._ensure_valid_token(timeout)

        def _fetch(url: str) -> dict:
            full_url = self.base_url + url
            response = call_session._request(url=full_url, method=RequestMethod(method))
            try:
                data = response.json()
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            output = list(executor.map(_fetch, urls))

        return output

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup session."""
        self.session.close()
        logger.debug("Session closed")
        return False
