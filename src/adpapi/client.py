import json
import logging
import os
import time
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from adpapi.sessions import ApiSession

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT = 30
TOKEN_BUFFER_SECONDS = 300  # Refresh token 5 minutes before expiration


class AdpApiClient:
    def __init__(
        self, client_id: str, client_secret: str, cert_path: str, key_path: str
    ):
        if not all([client_id, client_secret, cert_path, key_path]):
            raise ValueError("All credentials and paths must be provided.")
        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            raise FileNotFoundError("Certificate or key file not found.")

        self.client_id = client_id
        self.client_secret = client_secret
        self.cert_path = cert_path
        self.key_path = key_path
        self.cert = (cert_path, key_path)
        self.session = requests.Session()
        self._setup_retry_strategy()

        # Token expiration tracking
        self.token = None
        self.token_expires_at = 0

    @property
    def payload(self) -> Dict[str, str]:
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
        logger.debug(
            f"Retry strategy configured: {retries} retries with {backoff_factor}s backoff"
        )

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

    def _get_headers(self, masked: bool = True) -> Dict[str, str]:
        """Build request headers with Bearer token and masking preference."""
        # * May need to be tweaked in the future if OData calls or other forms are needed. Not necessary for MVP
        accept = "application/json"
        if not masked:
            accept += ";masked=false"
            logging.debug(f'Calling _get_headers with accept = {accept}')
            
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": accept,
        }
        
        return headers 

    def get_masked_headers(self) -> Dict[str,str]:
        return self._get_headers(True)
    def get_unmasked_headers(self) -> Dict[str, str]:
        return self._get_headers(False)

    def call_endpoint(
        self,
        endpoint: str,
        cols: List[str],
        masked: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
        page_size: int = 100,
        max_requests: Optional[int] = None,
    ) -> List[Dict]:
        """Call any Registered ADP Endpoint

        Args:
            endpoint (str): API Endpoint or qualified URL to call
            cols (List[str]): Table Columns to pull
            masked (bool, optional): Mask Sensitive Columns Containing Personally Identifiable Information. Defaults to True.
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
            logger.warning(
                "Page size > 100 not supported by API endpoint. Limiting to 100."
            )
            page_size = 100

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

        # Output/Request Initialization
        output = []
        select = ",".join(cols)
        skip = 0
        url = self.base_url + endpoint
        
        if masked:
            get_headers_fn = self.get_masked_headers
        else:
            get_headers_fn = self.get_unmasked_headers
        
        call_session = ApiSession(self.session, self.cert, get_headers_fn, timeout=timeout)
        while True:
            params = {
                "$top": page_size,
                "$skip": skip,
                "$select": select,
            }
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

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup session."""
        self.session.close()
        logger.debug("Session closed")
        return False
