from unittest.mock import MagicMock

import pytest
import requests

from adpapi.sessions import ApiSession, RequestMethod


@pytest.fixture
def mock_session():
    """Provide a mocked requests.Session."""
    return MagicMock(spec=requests.Session)


@pytest.fixture
def cert():
    """Provide test certificate tuple."""
    return ("cert.pem", "key.key")


@pytest.fixture
def api_session(mock_session, cert):
    """Provide a basic ApiSession instance."""
    return ApiSession(mock_session, cert)


@pytest.fixture
def api_session_with_headers(mock_session, cert):
    """Provide an ApiSession with custom get_headers callable."""
    def get_headers_fn():
        return {"Authorization": "Bearer token"}

    return ApiSession(
        mock_session,
        cert,
        get_headers=get_headers_fn,
        params={"$top": 100},
        timeout=30,
    )


class TestApiSessionInitialization:
    """Test ApiSession initialization and setup."""

    def test_initialization_default_values(self, api_session, mock_session, cert):
        """Test ApiSession initializes with default values."""
        assert api_session.session == mock_session
        assert api_session.cert == cert
        assert api_session.get_headers() == {}  # get_headers callable returns empty dict
        assert api_session.params == {}
        assert api_session.timeout == 30
        assert api_session.data is None

    def test_initialization_with_custom_values(self, mock_session, cert):
        """Test ApiSession initializes with custom values."""
        def get_headers_fn():
            return {"Authorization": "Bearer token"}

        params = {"$top": 100}

        api_session = ApiSession(
            mock_session,
            cert,
            get_headers=get_headers_fn,
            params=params,
            timeout=60,
        )

        assert api_session.get_headers() == {"Authorization": "Bearer token"}
        assert api_session.params == params
        assert api_session.timeout == 60


class TestApiSessionSetters:
    """Test ApiSession setter methods."""

    def test_set_params(self, api_session):
        """Test setting parameters."""
        params = {"$top": 50, "$skip": 0}
        api_session.set_params(params)

        assert api_session.params == params

    def test_set_data(self, api_session):
        """Test setting request data."""
        data = {"key": "value"}
        api_session.set_data(data)

        assert api_session.data == data


class TestRequestMethod:
    """Test RequestMethod enum."""

    def test_request_methods_exist(self):
        """Test all expected HTTP methods exist."""
        assert RequestMethod.GET == "GET"
        assert RequestMethod.POST == "POST"
        assert RequestMethod.PUT == "PUT"
        assert RequestMethod.DELETE == "DELETE"


class TestGetRequestFunction:
    """Test _get_request_function method."""

    def test_get_request_function_get(self, api_session, mock_session):
        """Test getting GET request function."""
        func = api_session._get_request_function(RequestMethod.GET)
        assert func == mock_session.get

    def test_get_request_function_post(self, api_session, mock_session):
        """Test getting POST request function."""
        func = api_session._get_request_function(RequestMethod.POST)
        assert func == mock_session.post

    def test_get_request_function_put(self, api_session, mock_session):
        """Test getting PUT request function."""
        func = api_session._get_request_function(RequestMethod.PUT)
        assert func == mock_session.put

    def test_get_request_function_delete(self, api_session, mock_session):
        """Test getting DELETE request function."""
        func = api_session._get_request_function(RequestMethod.DELETE)
        assert func == mock_session.delete

    def test_get_request_function_invalid(self, api_session):
        """Test getting unsupported request function raises error."""
        with pytest.raises(ValueError) as exc_info:
            api_session._get_request_function("INVALID")

        assert "Unsupported method" in str(exc_info.value)


class TestRequest:
    """Test _request method."""

    def test_request_get_success(self, api_session_with_headers, mock_session):
        """Test successful GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        response = api_session_with_headers._request(
            "http://example.com", RequestMethod.GET
        )

        assert response == mock_response
        mock_session.get.assert_called_once()

    def test_request_post_with_data(self, api_session_with_headers, mock_session):
        """Test POST request with JSON data."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_session.post.return_value = mock_response

        api_session_with_headers.data = {"key": "value"}
        response = api_session_with_headers._request(
            "http://example.com", RequestMethod.POST
        )

        assert response == mock_response
        # Verify json kwarg was passed
        call_kwargs = mock_session.post.call_args[1]
        assert "json" in call_kwargs
        assert call_kwargs["json"] == {"key": "value"}

    def test_request_exception_handling(self, api_session, mock_session):
        """Test request exception handling."""
        mock_session.get.side_effect = requests.RequestException("Connection failed")

        with pytest.raises(requests.RequestException):
            api_session._request("http://example.com", RequestMethod.GET)

    def test_request_calls_raise_for_status(self, api_session, mock_session):
        """Test that raise_for_status is called."""
        mock_response = MagicMock()
        mock_session.get.return_value = mock_response

        api_session._request("http://example.com", RequestMethod.GET)

        mock_response.raise_for_status.assert_called_once()


class TestHttpMethods:
    """Test HTTP method wrappers."""

    def test_get_method(self, api_session, mock_session):
        """Test GET method wrapper."""
        mock_response = MagicMock()
        mock_session.get.return_value = mock_response

        response = api_session.get("http://example.com")

        assert response == mock_response
        mock_session.get.assert_called_once()

    def test_post_method_without_data(self, api_session, mock_session):
        """Test POST method wrapper without data."""
        mock_response = MagicMock()
        mock_session.post.return_value = mock_response

        response = api_session.post("http://example.com")

        assert response == mock_response

    def test_post_method_with_data(self, api_session, mock_session):
        """Test POST method wrapper with data."""
        mock_response = MagicMock()
        mock_session.post.return_value = mock_response

        data = {"key": "value"}
        response = api_session.post("http://example.com", data=data)

        assert response == mock_response
        assert api_session.data == data

    def test_put_method_with_data(self, api_session, mock_session):
        """Test PUT method wrapper with data."""
        mock_response = MagicMock()
        mock_session.put.return_value = mock_response

        data = {"key": "updated_value"}
        response = api_session.put("http://example.com", data=data)

        assert response == mock_response
        assert api_session.data == data

    def test_delete_method(self, api_session, mock_session):
        """Test DELETE method wrapper."""
        mock_response = MagicMock()
        mock_session.delete.return_value = mock_response

        response = api_session.delete("http://example.com")

        assert response == mock_response
        mock_session.delete.assert_called_once()


class TestRequestParameters:
    """Test request parameter passing."""

    def test_request_includes_all_parameters(self, mock_session, cert):
        """Test that all parameters are passed to request function."""
        def get_headers_fn():
            return {"Authorization": "Bearer token", "Custom": "Header"}

        params = {"$top": 100, "$skip": 50}
        timeout = 60

        api_session = ApiSession(
            mock_session,
            cert,
            get_headers=get_headers_fn,
            params=params,
            timeout=timeout,
        )

        mock_response = MagicMock()
        mock_session.get.return_value = mock_response

        api_session.get("http://example.com")

        # Verify all parameters were passed
        call_kwargs = mock_session.get.call_args[1]
        assert call_kwargs["headers"] == {"Authorization": "Bearer token", "Custom": "Header"}
        assert call_kwargs["params"] == params
        assert call_kwargs["cert"] == cert
        assert call_kwargs["timeout"] == timeout
