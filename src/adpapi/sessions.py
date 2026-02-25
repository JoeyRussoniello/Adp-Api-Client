"""Session management and API request utilities for the ADP API client.

This module provides session and request handling utilities including the ApiSession
dataclass for managing authenticated HTTP sessions and the RequestMethod enum for
specifying HTTP request types.
"""

import json
import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Optional

import requests

logger = logging.getLogger(__name__)


class RequestMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


@dataclass
class ApiSession:
    session: requests.Session
    cert: tuple[str, str]
    get_headers: Optional[Callable[[], dict]] = None
    headers: Optional[dict] = None
    params: Optional[dict] = None
    timeout: int = 30
    data: Optional[Any] = None

    def __post_init__(self):
        if self.get_headers is None:
            # Default to empty header generation
            self.get_headers = lambda: {}
        if self.params is None:
            self.params = {}

    def set_params(self, params: dict):
        self.params = params

    def set_data(self, data: Any):
        self.data = data

    def _get_request_function(self, method: RequestMethod) -> Callable:
        match method:
            case RequestMethod.GET:
                return self.session.get
            case RequestMethod.POST:
                return self.session.post
            case RequestMethod.PUT:
                return self.session.put
            case RequestMethod.DELETE:
                return self.session.delete

        raise ValueError(f"Unsupported method {method}")

    def _request(
        self, url: str, method: RequestMethod = RequestMethod.GET
    ) -> requests.Response:
        """Execute HTTP request with specified method, headers, params, and optional data.

        Args:
            url: The request URL
            method: HTTP method (GET, POST, PUT, DELETE)

        Returns:
            requests.Response object

        Raises:
            requests.RequestException: If request fails
        """
        request_fn = self._get_request_function(method)
        # Generate headers on call time for up-to-date token
        assert self.get_headers is not None
        headers = self.get_headers()
        kwargs = {
            "headers": headers,
            "params": self.params,
            "cert": self.cert,
            "timeout": self.timeout,
        }
        if self.data is not None:
            kwargs["json"] = self.data
        response = request_fn(url, **kwargs)

        try:
            response.raise_for_status()

        except requests.RequestException as e:
            headers = dict(response.headers)
            data = response.json()
            logger.error(
                f"Request failed for {method} request to url: {url} with params {self.params}\n"
                f"Response Headers: {json.dumps(headers, indent=2)}\n"
                f"Response Body: {json.dumps(data, indent=2)}\n"
                f"Error:\n{e}"
            )
            raise

        return response

    def get(self, url: str) -> requests.Response:
        return self._request(url, RequestMethod.GET)

    def post(self, url: str, data: Optional[Any] = None) -> requests.Response:
        if data is not None:
            self.set_data(data)
        return self._request(url, RequestMethod.POST)

    def put(self, url: str, data: Optional[Any] = None) -> requests.Response:
        if data is not None:
            self.set_data(data)
        return self._request(url, RequestMethod.PUT)

    def delete(self, url: str) -> requests.Response:
        return self._request(url, RequestMethod.DELETE)
