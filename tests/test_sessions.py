import os
import sys
import unittest
from unittest.mock import MagicMock

import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sessions import ApiSession, RequestMethod


class TestApiSessionInitialization(unittest.TestCase):
    """Test ApiSession initialization and setup."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock(spec=requests.Session)
        self.cert = ("cert.pem", "key.key")

    def test_initialization_default_values(self):
        """Test ApiSession initializes with default values."""
        api_session = ApiSession(self.mock_session, self.cert)

        self.assertEqual(api_session.session, self.mock_session)
        self.assertEqual(api_session.cert, self.cert)
        self.assertEqual(api_session.headers, {})
        self.assertEqual(api_session.params, {})
        self.assertEqual(api_session.timeout, 30)
        self.assertIsNone(api_session.data)

    def test_initialization_with_custom_values(self):
        """Test ApiSession initializes with custom values."""
        headers = {"Authorization": "Bearer token"}
        params = {"$top": 100}

        api_session = ApiSession(
            self.mock_session,
            self.cert,
            headers=headers,
            params=params,
            timeout=60,
        )

        self.assertEqual(api_session.headers, headers)
        self.assertEqual(api_session.params, params)
        self.assertEqual(api_session.timeout, 60)


class TestApiSessionSetters(unittest.TestCase):
    """Test ApiSession setter methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock(spec=requests.Session)
        self.cert = ("cert.pem", "key.key")
        self.api_session = ApiSession(self.mock_session, self.cert)

    def test_set_params(self):
        """Test setting parameters."""
        params = {"$top": 50, "$skip": 0}
        self.api_session.set_params(params)

        self.assertEqual(self.api_session.params, params)

    def test_set_data(self):
        """Test setting request data."""
        data = {"key": "value"}
        self.api_session.set_data(data)

        self.assertEqual(self.api_session.data, data)


class TestRequestMethod(unittest.TestCase):
    """Test RequestMethod enum."""

    def test_request_methods_exist(self):
        """Test all expected HTTP methods exist."""
        self.assertEqual(RequestMethod.GET, "GET")
        self.assertEqual(RequestMethod.POST, "POST")
        self.assertEqual(RequestMethod.PUT, "PUT")
        self.assertEqual(RequestMethod.DELETE, "DELETE")


class TestGetRequestFunction(unittest.TestCase):
    """Test _get_request_function method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock(spec=requests.Session)
        self.cert = ("cert.pem", "key.key")
        self.api_session = ApiSession(self.mock_session, self.cert)

    def test_get_request_function_get(self):
        """Test getting GET request function."""
        func = self.api_session._get_request_function(RequestMethod.GET)
        self.assertEqual(func, self.mock_session.get)

    def test_get_request_function_post(self):
        """Test getting POST request function."""
        func = self.api_session._get_request_function(RequestMethod.POST)
        self.assertEqual(func, self.mock_session.post)

    def test_get_request_function_put(self):
        """Test getting PUT request function."""
        func = self.api_session._get_request_function(RequestMethod.PUT)
        self.assertEqual(func, self.mock_session.put)

    def test_get_request_function_delete(self):
        """Test getting DELETE request function."""
        func = self.api_session._get_request_function(RequestMethod.DELETE)
        self.assertEqual(func, self.mock_session.delete)

    def test_get_request_function_invalid(self):
        """Test getting unsupported request function raises error."""
        with self.assertRaises(ValueError) as context:
            self.api_session._get_request_function("INVALID")

        self.assertIn("Unsupported method", str(context.exception))


class TestRequest(unittest.TestCase):
    """Test _request method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock(spec=requests.Session)
        self.cert = ("cert.pem", "key.key")
        self.api_session = ApiSession(
            self.mock_session,
            self.cert,
            headers={"Authorization": "Bearer token"},
            timeout=30,
        )

    def test_request_get_success(self):
        """Test successful GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        self.mock_session.get.return_value = mock_response

        response = self.api_session._request("http://example.com", RequestMethod.GET)

        self.assertEqual(response, mock_response)
        self.mock_session.get.assert_called_once()

    def test_request_post_with_data(self):
        """Test POST request with JSON data."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        self.mock_session.post.return_value = mock_response

        self.api_session.data = {"key": "value"}
        response = self.api_session._request("http://example.com", RequestMethod.POST)

        self.assertEqual(response, mock_response)
        # Verify json kwarg was passed
        call_kwargs = self.mock_session.post.call_args[1]
        self.assertIn("json", call_kwargs)
        self.assertEqual(call_kwargs["json"], {"key": "value"})

    def test_request_exception_handling(self):
        """Test request exception handling."""
        self.mock_session.get.side_effect = requests.RequestException(
            "Connection failed"
        )

        with self.assertRaises(requests.RequestException):
            self.api_session._request("http://example.com", RequestMethod.GET)

    def test_request_calls_raise_for_status(self):
        """Test that raise_for_status is called."""
        mock_response = MagicMock()
        self.mock_session.get.return_value = mock_response

        self.api_session._request("http://example.com", RequestMethod.GET)

        mock_response.raise_for_status.assert_called_once()


class TestHttpMethods(unittest.TestCase):
    """Test HTTP method wrappers."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock(spec=requests.Session)
        self.cert = ("cert.pem", "key.key")
        self.api_session = ApiSession(self.mock_session, self.cert)

    def test_get_method(self):
        """Test GET method wrapper."""
        mock_response = MagicMock()
        self.mock_session.get.return_value = mock_response

        response = self.api_session.get("http://example.com")

        self.assertEqual(response, mock_response)
        self.mock_session.get.assert_called_once()

    def test_post_method_without_data(self):
        """Test POST method wrapper without data."""
        mock_response = MagicMock()
        self.mock_session.post.return_value = mock_response

        response = self.api_session.post("http://example.com")

        self.assertEqual(response, mock_response)

    def test_post_method_with_data(self):
        """Test POST method wrapper with data."""
        mock_response = MagicMock()
        self.mock_session.post.return_value = mock_response

        data = {"key": "value"}
        response = self.api_session.post("http://example.com", data=data)

        self.assertEqual(response, mock_response)
        self.assertEqual(self.api_session.data, data)

    def test_put_method_with_data(self):
        """Test PUT method wrapper with data."""
        mock_response = MagicMock()
        self.mock_session.put.return_value = mock_response

        data = {"key": "updated_value"}
        response = self.api_session.put("http://example.com", data=data)

        self.assertEqual(response, mock_response)
        self.assertEqual(self.api_session.data, data)

    def test_delete_method(self):
        """Test DELETE method wrapper."""
        mock_response = MagicMock()
        self.mock_session.delete.return_value = mock_response

        response = self.api_session.delete("http://example.com")

        self.assertEqual(response, mock_response)
        self.mock_session.delete.assert_called_once()


class TestRequestParameters(unittest.TestCase):
    """Test request parameter passing."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock(spec=requests.Session)
        self.cert = ("cert.pem", "key.key")

    def test_request_includes_all_parameters(self):
        """Test that all parameters are passed to request function."""
        headers = {"Authorization": "Bearer token", "Custom": "Header"}
        params = {"$top": 100, "$skip": 50}
        timeout = 60

        api_session = ApiSession(
            self.mock_session,
            self.cert,
            headers=headers,
            params=params,
            timeout=timeout,
        )

        mock_response = MagicMock()
        self.mock_session.get.return_value = mock_response

        api_session.get("http://example.com")

        # Verify all parameters were passed
        call_kwargs = self.mock_session.get.call_args[1]
        self.assertEqual(call_kwargs["headers"], headers)
        self.assertEqual(call_kwargs["params"], params)
        self.assertEqual(call_kwargs["cert"], self.cert)
        self.assertEqual(call_kwargs["timeout"], timeout)


if __name__ == "__main__":
    unittest.main()
