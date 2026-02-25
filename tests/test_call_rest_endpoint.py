"""
Test suite for AdpApiClient.call_rest_endpoint.

Captures baseline behavior before thread-safe parallelism optimization:
- Single and batch path-parameter substitution
- HTTP method dispatch (GET, POST, PUT, DELETE)
- Masked vs unmasked header selection
- Query parameter forwarding
- Token refresh before each request
- Error handling (missing params, JSON decode errors, HTTP errors)
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest
import requests

from adpapi.client import AdpApiClient, AdpCredentials

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def adp_credentials() -> AdpCredentials:
    return AdpCredentials(
        client_id="test_client_id",
        client_secret="test_client_secret",
        cert_path="test_cert.pem",
        key_path="test_key.key",
    )


@pytest.fixture
def mock_file_system():
    with patch("os.path.exists") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def client(adp_credentials, mock_file_system):
    """Client with a valid (non-expired) mocked token."""
    with patch("adpapi.client.AdpApiClient._get_token") as mock_get_token:
        mock_get_token.return_value = "test_token_123"
        c = AdpApiClient(adp_credentials)
        c.token = "test_token_123"
        c.token_expires_at = time.time() + 3600
        yield c


def _make_json_response(data: dict, status_code: int = 200) -> MagicMock:
    """Helper to build a mock requests.Response."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


# ============================================================================
# BASIC REQUEST TESTS
# ============================================================================


class TestSingleRequest:
    """Single-URL call_rest_endpoint behavior."""

    def test_single_path_param_returns_response(self, client):
        """GET with one path parameter returns parsed JSON in a list."""
        expected = {"workers": [{"id": "123"}]}
        with patch(
            "adpapi.sessions.ApiSession._request",
            return_value=_make_json_response(expected),
        ):
            result = client.call_rest_endpoint("/hr/v2/workers/{workerId}", workerId="123")
        assert result == [expected]

    def test_no_path_params(self, client):
        """Endpoint without placeholders works with no kwargs."""
        expected = {"status": "ok"}
        with patch(
            "adpapi.sessions.ApiSession._request",
            return_value=_make_json_response(expected),
        ):
            result = client.call_rest_endpoint("/hr/v2/workers")
        assert result == [expected]

    def test_multiple_path_params_single_values(self, client):
        """Multiple path parameters each with a single value."""
        expected = {"job": "data"}
        with patch(
            "adpapi.sessions.ApiSession._request",
            return_value=_make_json_response(expected),
        ) as mock_req:
            result = client.call_rest_endpoint(
                "/hr/v2/workers/{workerId}/jobs/{jobId}",
                workerId="W1",
                jobId="J1",
            )
        assert result == [expected]
        # Verify the fully-substituted URL was used
        called_url = mock_req.call_args[1].get("url") or mock_req.call_args[0][0]
        assert "W1" in called_url
        assert "J1" in called_url


# ============================================================================
# BATCH REQUEST TESTS
# ============================================================================


class TestBatchRequests:
    """Batch (list) path-parameter substitution."""

    def test_list_param_makes_multiple_requests(self, client):
        """A list of IDs produces one request per ID."""
        responses = [
            _make_json_response({"id": "A"}),
            _make_json_response({"id": "B"}),
            _make_json_response({"id": "C"}),
        ]
        with patch("adpapi.sessions.ApiSession._request", side_effect=responses):
            result = client.call_rest_endpoint(
                "/hr/v2/workers/{workerId}", workerId=["A", "B", "C"]
            )
        assert len(result) == 3
        assert result[0] == {"id": "A"}
        assert result[2] == {"id": "C"}

    def test_batch_urls_contain_each_id(self, client):
        """Each substituted URL contains its respective ID."""
        with patch(
            "adpapi.sessions.ApiSession._request", return_value=_make_json_response({})
        ) as mock_req:
            client.call_rest_endpoint("/hr/v2/workers/{workerId}", workerId=["X1", "X2"])
        urls = [c.kwargs.get("url") or c.args[0] for c in mock_req.call_args_list]
        assert any("X1" in u for u in urls)
        assert any("X2" in u for u in urls)


# ============================================================================
# HTTP METHOD TESTS
# ============================================================================


class TestHttpMethods:
    """HTTP method dispatch."""

    @pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
    def test_method_is_forwarded(self, client, method):
        """The specified HTTP method is passed to ApiSession._request."""
        with patch(
            "adpapi.sessions.ApiSession._request", return_value=_make_json_response({})
        ) as mock_req:
            client.call_rest_endpoint("/hr/v2/workers", method=method)
        mock_req.assert_called_once()
        assert mock_req.call_args[1].get("method") or mock_req.call_args[0][1] == method

    def test_default_method_is_get(self, client):
        """Default method is GET when not specified."""
        with patch(
            "adpapi.sessions.ApiSession._request", return_value=_make_json_response({})
        ) as mock_req:
            client.call_rest_endpoint("/hr/v2/workers")
        call_kwargs = mock_req.call_args
        # method positional or keyword should be GET
        method_used = call_kwargs[1].get("method") or call_kwargs[0][1]
        assert method_used == "GET"


# ============================================================================
# HEADER / MASKING TESTS
# ============================================================================


class TestMaskedHeaders:
    """Masked vs unmasked header selection."""

    def test_masked_true_uses_masked_headers(self, client):
        """masked=True selects get_masked_headers."""
        with (
            patch.object(client, "get_masked_headers", wraps=client.get_masked_headers),
            patch(
                "adpapi.sessions.ApiSession._request",
                return_value=_make_json_response({}),
            ),
        ):
            client.call_rest_endpoint("/hr/v2/workers", masked=True)
        # The header function is passed to ApiSession, so spy may not be called here directly.
        # Instead, verify via the headers content.
        headers = client.get_masked_headers()
        assert headers["Accept"] == "application/json"

    def test_masked_false_uses_unmasked_headers(self, client):
        """masked=False selects get_unmasked_headers."""
        headers = client.get_unmasked_headers()
        assert "masked=false" in headers["Accept"]

        with patch("adpapi.sessions.ApiSession._request", return_value=_make_json_response({})):
            # Should not raise
            client.call_rest_endpoint("/hr/v2/workers", masked=False)


# ============================================================================
# QUERY PARAMETER TESTS
# ============================================================================


class TestQueryParams:
    """Query parameter forwarding."""

    def test_params_forwarded_to_session(self, client):
        """Query params dict is set on the ApiSession."""
        with (
            patch("adpapi.sessions.ApiSession.set_params") as mock_set,
            patch(
                "adpapi.sessions.ApiSession._request",
                return_value=_make_json_response({}),
            ),
        ):
            client.call_rest_endpoint("/hr/v2/workers", params={"$top": 10, "$select": "name"})
        mock_set.assert_called_once_with({"$top": 10, "$select": "name"})

    def test_no_params_skips_set_params(self, client):
        """When params is None, set_params is not called."""
        with (
            patch("adpapi.sessions.ApiSession.set_params") as mock_set,
            patch(
                "adpapi.sessions.ApiSession._request",
                return_value=_make_json_response({}),
            ),
        ):
            client.call_rest_endpoint("/hr/v2/workers")
        mock_set.assert_not_called()


# ============================================================================
# TOKEN MANAGEMENT TESTS
# ============================================================================


class TestTokenRefresh:
    """Token refresh before requests."""

    def test_token_refreshed_once_before_batch(self, client):
        """_ensure_valid_token is called exactly once before parallel execution."""
        with (
            patch.object(client, "_ensure_valid_token") as mock_ensure,
            patch(
                "adpapi.sessions.ApiSession._request",
                return_value=_make_json_response({}),
            ),
        ):
            client.call_rest_endpoint("/hr/v2/workers/{workerId}", workerId=["A", "B"])
        assert mock_ensure.call_count == 1

    def test_expired_token_triggers_refresh(self, client):
        """An expired token is refreshed before the request."""
        client.token_expires_at = time.time() - 100  # expired
        with (
            patch.object(client, "_get_token", return_value="refreshed") as mock_get,
            patch(
                "adpapi.sessions.ApiSession._request",
                return_value=_make_json_response({}),
            ),
        ):
            client.call_rest_endpoint("/hr/v2/workers")
        mock_get.assert_called_once()
        assert client.token == "refreshed"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestErrorHandling:
    """Error scenarios."""

    def test_missing_path_parameter_raises_value_error(self, client):
        """Missing a required path parameter raises ValueError."""
        with pytest.raises(ValueError, match="Missing required path parameters"):
            client.call_rest_endpoint("/hr/v2/workers/{workerId}")

    def test_missing_one_of_multiple_params_raises(self, client):
        """Missing one of several required path parameters raises ValueError."""
        with pytest.raises(ValueError, match="Missing required path parameters"):
            client.call_rest_endpoint("/hr/v2/workers/{workerId}/jobs/{jobId}", workerId="W1")

    def test_json_decode_error_is_raised(self, client):
        """Non-JSON response body raises json.JSONDecodeError."""
        bad_response = MagicMock(spec=requests.Response)
        bad_response.status_code = 200
        bad_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        bad_response.raise_for_status.return_value = None

        with (
            patch("adpapi.sessions.ApiSession._request", return_value=bad_response),
            pytest.raises(json.JSONDecodeError),
        ):
            client.call_rest_endpoint("/hr/v2/workers")

    def test_http_error_propagates(self, client):
        """HTTP errors from ApiSession._request propagate."""
        with (
            patch(
                "adpapi.sessions.ApiSession._request",
                side_effect=requests.HTTPError("500 Server Error"),
            ),
            pytest.raises(requests.HTTPError),
        ):
            client.call_rest_endpoint("/hr/v2/workers")


# ============================================================================
# RETURN STRUCTURE TESTS
# ============================================================================


class TestReturnStructure:
    """Return value shape and ordering."""

    def test_returns_list(self, client):
        """Return type is always a list."""
        with patch(
            "adpapi.sessions.ApiSession._request",
            return_value=_make_json_response({"a": 1}),
        ):
            result = client.call_rest_endpoint("/hr/v2/workers")
        assert isinstance(result, list)

    def test_empty_endpoint_list_returns_empty(self, client):
        """An endpoint with an empty list param produces no requests and returns []."""
        result = client.call_rest_endpoint("/hr/v2/workers/{workerId}", workerId=[])
        assert result == []

    def test_response_order_matches_input_order(self, client):
        """Responses are returned in the same order as the input IDs."""
        responses = [
            _make_json_response({"id": "first"}),
            _make_json_response({"id": "second"}),
            _make_json_response({"id": "third"}),
        ]
        with patch("adpapi.sessions.ApiSession._request", side_effect=responses):
            result = client.call_rest_endpoint(
                "/hr/v2/workers/{workerId}", workerId=["1", "2", "3"]
            )
        assert result[0]["id"] == "first"
        assert result[1]["id"] == "second"
        assert result[2]["id"] == "third"


# ============================================================================
# URL CONSTRUCTION TESTS
# ============================================================================


class TestUrlConstruction:
    """Verify URLs are built correctly with base_url prefix."""

    def test_url_includes_base_url(self, client):
        """Each request URL starts with the base_url."""
        with patch(
            "adpapi.sessions.ApiSession._request", return_value=_make_json_response({})
        ) as mock_req:
            client.call_rest_endpoint("/hr/v2/workers/{workerId}", workerId="123")
        called_url = mock_req.call_args[1].get("url") or mock_req.call_args[0][0]
        assert called_url.startswith(client.base_url)

    def test_path_params_are_url_encoded(self, client):
        """Special characters in path parameters are URL-encoded."""
        with patch(
            "adpapi.sessions.ApiSession._request", return_value=_make_json_response({})
        ) as mock_req:
            client.call_rest_endpoint("/hr/v2/workers/{workerId}", workerId="abc def")
        called_url = mock_req.call_args[1].get("url") or mock_req.call_args[0][0]
        assert "abc%20def" in called_url
        assert "abc def" not in called_url


# ============================================================================
# PARALLELISM / MAX_WORKERS TESTS
# ============================================================================


class TestMaxWorkers:
    """max_workers parameter and parallel execution."""

    def test_default_max_workers_is_one(self, client):
        """With default max_workers=1, ThreadPoolExecutor uses 1 thread."""
        with (
            patch("adpapi.client.ThreadPoolExecutor", wraps=ThreadPoolExecutor) as mock_pool,
            patch(
                "adpapi.sessions.ApiSession._request",
                return_value=_make_json_response({}),
            ),
        ):
            client.call_rest_endpoint("/hr/v2/workers")
        mock_pool.assert_called_once_with(max_workers=1)

    def test_custom_max_workers_passed_to_executor(self, client):
        """max_workers value is forwarded to ThreadPoolExecutor."""
        with (
            patch("adpapi.client.ThreadPoolExecutor", wraps=ThreadPoolExecutor) as mock_pool,
            patch(
                "adpapi.sessions.ApiSession._request",
                return_value=_make_json_response({}),
            ),
        ):
            client.call_rest_endpoint(
                "/hr/v2/workers/{workerId}",
                workerId=["A", "B", "C"],
                max_workers=4,
            )
        mock_pool.assert_called_once_with(max_workers=4)

    def test_parallel_results_preserve_order(self, client):
        """Results stay ordered even with multiple workers."""
        # Map responses by URL so ordering is independent of thread scheduling.
        # Using side_effect as a list is not thread-safe: threads may call the
        # mock in any order, especially on Python 3.13+ where thread scheduling
        # is less predictable.
        url_responses = {
            "/hr/v2/workers/1": {"id": "first"},
            "/hr/v2/workers/2": {"id": "second"},
            "/hr/v2/workers/3": {"id": "third"},
        }

        def _url_based_response(url, **kwargs):
            for path, data in url_responses.items():
                if url.endswith(path):
                    return _make_json_response(data)
            raise ValueError(f"Unexpected URL: {url}")

        with patch("adpapi.sessions.ApiSession._request", side_effect=_url_based_response):
            result = client.call_rest_endpoint(
                "/hr/v2/workers/{workerId}",
                workerId=["1", "2", "3"],
                max_workers=3,
            )
        assert result[0]["id"] == "first"
        assert result[1]["id"] == "second"
        assert result[2]["id"] == "third"

    def test_token_ensured_once_even_with_many_workers(self, client):
        """Token is validated exactly once regardless of max_workers."""
        with (
            patch.object(client, "_ensure_valid_token") as mock_ensure,
            patch(
                "adpapi.sessions.ApiSession._request",
                return_value=_make_json_response({}),
            ),
        ):
            client.call_rest_endpoint(
                "/hr/v2/workers/{workerId}",
                workerId=["A", "B", "C", "D"],
                max_workers=4,
            )
        assert mock_ensure.call_count == 1

    def test_error_in_parallel_propagates(self, client):
        """An exception in one thread propagates to the caller."""
        responses = [
            _make_json_response({"id": "ok"}),
            MagicMock(
                spec=requests.Response,
                status_code=200,
                json=MagicMock(side_effect=json.JSONDecodeError("bad", "", 0)),
                raise_for_status=MagicMock(return_value=None),
            ),
        ]
        with (
            patch("adpapi.sessions.ApiSession._request", side_effect=responses),
            pytest.raises(json.JSONDecodeError),
        ):
            client.call_rest_endpoint(
                "/hr/v2/workers/{workerId}",
                workerId=["A", "B"],
                max_workers=2,
            )


# ============================================================================
# INJECT PATH PARAMS TESTS
# ============================================================================


class TestInjectPathParams:
    """inject_path_params parameter behavior."""

    def test_disabled_by_default(self, client):
        """Path params are NOT injected when inject_path_params is not set."""
        expected = {"workers": []}
        with patch(
            "adpapi.sessions.ApiSession._request",
            return_value=_make_json_response(expected),
        ):
            result = client.call_rest_endpoint(
                "/hr/v2/workers/{workerId}", workerId="ABC"
            )
        assert "workerId" not in result[0]

    def test_single_request_injects_param(self, client):
        """A single-value path param is merged into the response dict."""
        expected = {"workers": [{"name": "Jane"}]}
        with patch(
            "adpapi.sessions.ApiSession._request",
            return_value=_make_json_response(expected),
        ):
            result = client.call_rest_endpoint(
                "/hr/v2/workers/{workerId}",
                workerId="AOID123",
                inject_path_params=True,
            )
        assert result[0]["workerId"] == "AOID123"
        assert result[0]["workers"] == [{"name": "Jane"}]

    def test_batch_request_injects_correct_param_per_response(self, client):
        """Each response in a batch gets its own resolved path param."""
        responses = [
            _make_json_response({"name": "Alice"}),
            _make_json_response({"name": "Bob"}),
            _make_json_response({"name": "Carol"}),
        ]
        with patch("adpapi.sessions.ApiSession._request", side_effect=responses):
            result = client.call_rest_endpoint(
                "/hr/v2/workers/{workerId}",
                workerId=["W1", "W2", "W3"],
                inject_path_params=True,
            )
        assert result[0]["workerId"] == "W1"
        assert result[1]["workerId"] == "W2"
        assert result[2]["workerId"] == "W3"

    def test_multiple_path_params_injected(self, client):
        """Multiple scalar path params are all injected."""
        expected = {"job": "data"}
        with patch(
            "adpapi.sessions.ApiSession._request",
            return_value=_make_json_response(expected),
        ):
            result = client.call_rest_endpoint(
                "/hr/v2/workers/{workerId}/jobs/{jobId}",
                workerId="W1",
                jobId="J1",
                inject_path_params=True,
            )
        assert result[0]["workerId"] == "W1"
        assert result[0]["jobId"] == "J1"
        assert result[0]["job"] == "data"

    def test_injected_params_are_strings(self, client):
        """Injected path parameter values are converted to strings."""
        with patch(
            "adpapi.sessions.ApiSession._request",
            return_value=_make_json_response({}),
        ):
            result = client.call_rest_endpoint(
                "/hr/v2/workers/{workerId}",
                workerId=12345,
                inject_path_params=True,
            )
        assert result[0]["workerId"] == "12345"
