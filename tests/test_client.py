import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import requests
from requests.adapters import HTTPAdapter

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import AdpApiClient


class TestAdpApiClientInitialization(unittest.TestCase):
    """Test AdpApiClient initialization and configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.cert_path = "test_cert.pem"
        self.key_path = "test_key.key"

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_initialization_success(self, mock_get_token, mock_exists):
        """Test successful client initialization."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        client = AdpApiClient(
            self.client_id, self.client_secret, self.cert_path, self.key_path
        )

        self.assertEqual(client.client_id, self.client_id)
        self.assertEqual(client.client_secret, self.client_secret)
        self.assertEqual(client.token, "test_token")
        mock_get_token.assert_called_once()

    def test_initialization_missing_credentials(self):
        """Test initialization fails with missing credentials."""
        with self.assertRaises(ValueError) as context:
            AdpApiClient("", self.client_secret, self.cert_path, self.key_path)
        self.assertIn(
            "All credentials and paths must be provided", str(context.exception)
        )

    @patch("os.path.exists")
    def test_initialization_missing_cert_file(self, mock_exists):
        """Test initialization fails when cert file doesn't exist."""
        mock_exists.return_value = False

        with self.assertRaises(FileNotFoundError):
            AdpApiClient(
                self.client_id, self.client_secret, self.cert_path, self.key_path
            )

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_initialization_token_failure(self, mock_get_token, mock_exists):
        """Test initialization handles token acquisition failure."""
        mock_exists.return_value = True
        mock_get_token.side_effect = requests.RequestException("Token request failed")

        with self.assertRaises(requests.RequestException):
            AdpApiClient(
                self.client_id, self.client_secret, self.cert_path, self.key_path
            )


class TestTokenManagement(unittest.TestCase):
    """Test token acquisition and expiration handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.cert_path = "test_cert.pem"
        self.key_path = "test_key.key"

    @patch("os.path.exists")
    @patch("requests.Session.post")
    def test_get_token_success(self, mock_post, mock_exists):
        """Test successful token acquisition."""
        mock_exists.return_value = True

        # Create a mock response with proper setup
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test_token_123",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = AdpApiClient(
            self.client_id, self.client_secret, self.cert_path, self.key_path
        )

        # Verify token and expiration were set
        self.assertIsNotNone(client.token)
        self.assertTrue(client.token_expires_at > 0)

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_is_token_expired_not_expired(self, mock_get_token, mock_exists):
        """Test token expiration check when token is valid."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        client = AdpApiClient(
            self.client_id, self.client_secret, self.cert_path, self.key_path
        )

        # Set expiration time to future
        client.token_expires_at = time.time() + 3600

        self.assertFalse(client._is_token_expired())

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_is_token_expired_expired(self, mock_get_token, mock_exists):
        """Test token expiration check when token is expired."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        client = AdpApiClient(
            self.client_id, self.client_secret, self.cert_path, self.key_path
        )

        # Set expiration time to past
        client.token_expires_at = time.time() - 100

        self.assertTrue(client._is_token_expired())

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_ensure_valid_token_refresh(self, mock_get_token, mock_exists):
        """Test token refresh when expired."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        client = AdpApiClient(
            self.client_id, self.client_secret, self.cert_path, self.key_path
        )

        # Expire the token
        client.token_expires_at = time.time() - 100

        # Reset mock to track new calls
        mock_get_token.reset_mock()
        mock_get_token.return_value = "refreshed_token"

        client._ensure_valid_token()

        mock_get_token.assert_called_once()


class TestRetryStrategy(unittest.TestCase):
    """Test retry strategy configuration."""

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_retry_strategy_configured(self, mock_get_token, mock_exists):
        """Test that retry strategy is properly configured."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        client = AdpApiClient(
            "test_client", "test_secret", "test_cert.pem", "test_key.key"
        )

        # Check that adapters are mounted
        self.assertIsInstance(client.session.get_adapter("http://"), HTTPAdapter)
        self.assertIsInstance(client.session.get_adapter("https://"), HTTPAdapter)


class TestRequestHeaders(unittest.TestCase):
    """Test request header generation."""

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_get_headers_with_masking(self, mock_get_token, mock_exists):
        """Test header generation with masking enabled."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        client = AdpApiClient(
            "test_client", "test_secret", "test_cert.pem", "test_key.key"
        )

        headers = client._get_headers(masked=True)

        self.assertEqual(headers["Authorization"], "Bearer test_token")
        self.assertEqual(headers["Accept"], "application/json")

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_get_headers_without_masking(self, mock_get_token, mock_exists):
        """Test header generation with masking disabled."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        client = AdpApiClient(
            "test_client", "test_secret", "test_cert.pem", "test_key.key"
        )

        headers = client._get_headers(masked=False)

        self.assertEqual(headers["Authorization"], "Bearer test_token")
        self.assertEqual(headers["Accept"], "application/json;masked=false")


class TestContextManager(unittest.TestCase):
    """Test context manager functionality."""

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_context_manager_enter_exit(self, mock_get_token, mock_exists):
        """Test context manager properly enters and exits."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        with AdpApiClient(
            "test_client", "test_secret", "test_cert.pem", "test_key.key"
        ) as client:
            self.assertIsNotNone(client.token)
            self.assertIsNotNone(client.session)

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_context_manager_closes_session(self, mock_get_token, mock_exists):
        """Test context manager closes session on exit."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        client = AdpApiClient(
            "test_client", "test_secret", "test_cert.pem", "test_key.key"
        )

        # Mock the session.close method
        client.session.close = MagicMock()

        with client:
            pass

        client.session.close.assert_called_once()


class TestCallEndpoint(unittest.TestCase):
    """Test API endpoint calling functionality."""

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_call_endpoint_validation_missing_slash(self, mock_get_token, mock_exists):
        """Test endpoint validation requires proper formatting."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        client = AdpApiClient(
            "test_client", "test_secret", "test_cert.pem", "test_key.key"
        )

        with self.assertRaises(ValueError) as context:
            client.call_endpoint("invalid_endpoint", ["col1", "col2"])

        self.assertIn("Incorrect Endpoint Received", str(context.exception))

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_call_endpoint_with_path(self, mock_get_token, mock_exists):
        """Test endpoint call with proper path format."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        client = AdpApiClient(
            "test_client", "test_secret", "test_cert.pem", "test_key.key"
        )

        # Mock the ApiSession
        with patch("client.ApiSession") as mock_api_session:
            mock_session_instance = MagicMock()
            mock_api_session.return_value = mock_session_instance

            # Mock response
            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_session_instance.get.return_value = mock_response

            result = client.call_endpoint(
                "/hr/v2/workers", ["col1", "col2"], max_requests=1
            )

            self.assertIsInstance(result, list)

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_call_endpoint_page_size_limit(self, mock_get_token, mock_exists):
        """Test page size is capped at 100."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        client = AdpApiClient(
            "test_client", "test_secret", "test_cert.pem", "test_key.key"
        )

        with patch("client.ApiSession") as mock_api_session:
            mock_session_instance = MagicMock()
            mock_api_session.return_value = mock_session_instance

            mock_response = MagicMock()
            mock_response.status_code = 204
            mock_session_instance.get.return_value = mock_response

            # Request page size of 500 (should be capped at 100)
            client.call_endpoint(
                "/hr/v2/workers", ["col1"], page_size=500, max_requests=1
            )

            # Check that set_params was called with $top=100
            mock_session_instance.set_params.assert_called()
            call_args = mock_session_instance.set_params.call_args[0][0]
            self.assertEqual(call_args["$top"], 100)


class TestErrorHandling(unittest.TestCase):
    """Test error handling in various scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.cert_path = "test_cert.pem"
        self.key_path = "test_key.key"

    @patch("os.path.exists")
    @patch("requests.Session.post")
    def test_token_request_no_token_in_response(self, mock_post, mock_exists):
        """Test handling of token response without access_token."""
        mock_exists.return_value = True

        mock_response = MagicMock()
        mock_response.json.return_value = {}  # No access_token
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            AdpApiClient(
                self.client_id, self.client_secret, self.cert_path, self.key_path
            )

        self.assertIn("No access token in response", str(context.exception))

    @patch("os.path.exists")
    @patch("client.AdpApiClient._get_token")
    def test_call_endpoint_json_decode_error(self, mock_get_token, mock_exists):
        """Test handling of JSON decode errors."""
        mock_exists.return_value = True
        mock_get_token.return_value = "test_token"

        client = AdpApiClient(
            "test_client", "test_secret", "test_cert.pem", "test_key.key"
        )

        with patch("client.ApiSession") as mock_api_session:
            mock_session_instance = MagicMock()
            mock_api_session.return_value = mock_session_instance

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_session_instance.get.return_value = mock_response

            with self.assertRaises(ValueError):
                client.call_endpoint("/hr/v2/workers", ["col1"])


if __name__ == "__main__":
    unittest.main()
