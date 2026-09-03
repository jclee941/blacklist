import requests
from unittest.mock import Mock, patch, call


def _mock_response(status_code=200, json_data=None, text=""):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = text
    return response


class TestIntervalSecondsToString:
    def test_hourly(self):
        from core.routes.api.collection.utils import interval_seconds_to_string

        assert interval_seconds_to_string(3600) == "hourly"

    def test_daily(self):
        from core.routes.api.collection.utils import interval_seconds_to_string

        assert interval_seconds_to_string(86400) == "daily"

    def test_weekly(self):
        from core.routes.api.collection.utils import interval_seconds_to_string

        assert interval_seconds_to_string(604800) == "weekly"

    def test_other_defaults_to_daily(self):
        from core.routes.api.collection.utils import interval_seconds_to_string

        assert interval_seconds_to_string(12345) == "daily"


class TestIntervalStringToSeconds:
    def test_hourly(self):
        from core.routes.api.collection.utils import interval_string_to_seconds

        assert interval_string_to_seconds("hourly") == 3600

    def test_daily(self):
        from core.routes.api.collection.utils import interval_string_to_seconds

        assert interval_string_to_seconds("daily") == 86400

    def test_weekly(self):
        from core.routes.api.collection.utils import interval_string_to_seconds

        assert interval_string_to_seconds("weekly") == 604800

    def test_other_defaults_to_daily(self):
        from core.routes.api.collection.utils import interval_string_to_seconds

        assert interval_string_to_seconds("monthly") == 86400


class TestCallCollectorApi:
    @patch("core.routes.api.collection.utils.COLLECTOR_SERVICE_URL", "https://test:8545")
    @patch("core.routes.api.collection.utils.requests.get")
    def test_get_success_returns_json(self, mock_get):
        from core.routes.api.collection.utils import call_collector_api

        mock_get.return_value = _mock_response(status_code=200, json_data={"status": "healthy"})

        result = call_collector_api("/health")

        assert result == {"status": "healthy"}
        mock_get.assert_called_once_with(
            "https://test:8545/health",
            timeout=10,
            verify="/run/blacklist/ca.crt",
        )

    @patch("core.routes.api.collection.utils.COLLECTOR_SERVICE_URL", "https://test:8545")
    @patch("core.routes.api.collection.utils.requests.post")
    def test_post_success_with_data(self, mock_post):
        from core.routes.api.collection.utils import call_collector_api

        payload = {"source": "REGTECH"}
        mock_post.return_value = _mock_response(status_code=200, json_data={"queued": True})

        result = call_collector_api("/collect", method="POST", data=payload)

        assert result == {"queued": True}
        mock_post.assert_called_once_with(
            "https://test:8545/collect",
            json=payload,
            timeout=30,
            verify="/run/blacklist/ca.crt",
        )

    @patch("core.routes.api.collection.utils.COLLECTOR_SERVICE_URL", "https://test:8545")
    @patch("core.routes.api.collection.utils.requests.get")
    def test_non_200_status_returns_error_dict(self, mock_get):
        from core.routes.api.collection.utils import call_collector_api

        mock_get.return_value = _mock_response(status_code=503, text="service unavailable")

        result = call_collector_api("/health")

        assert result["success"] is False
        assert result["error"] == "Collector API error: 503"
        assert "details" not in result

    @patch("core.routes.api.collection.utils.requests.get")
    @patch("core.routes.api.collection.utils.requests.post")
    def test_unsupported_method_returns_error(self, mock_post, mock_get):
        from core.routes.api.collection.utils import call_collector_api

        result = call_collector_api("/health", method="PUT")

        assert result == {"success": False, "error": "Unsupported method: PUT"}
        mock_get.assert_not_called()
        mock_post.assert_not_called()

    @patch("core.routes.api.collection.utils.COLLECTOR_SERVICE_URL", "https://test:8545")
    @patch("core.routes.api.collection.utils.time.sleep")
    @patch("core.routes.api.collection.utils.requests.get")
    def test_connection_error_retries_three_times_then_returns_error(self, mock_get, mock_sleep):
        from core.routes.api.collection.utils import call_collector_api

        mock_get.side_effect = requests.exceptions.ConnectionError("connection refused")

        result = call_collector_api("/health")

        assert result["success"] is False
        assert result["error"] == "Cannot connect to collector service"
        assert "details" not in result
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("core.routes.api.collection.utils.COLLECTOR_SERVICE_URL", "https://test:8545")
    @patch("core.routes.api.collection.utils.time.sleep")
    @patch("core.routes.api.collection.utils.requests.get")
    def test_timeout_retries_three_times_then_returns_error(self, mock_get, mock_sleep):
        from core.routes.api.collection.utils import call_collector_api

        mock_get.side_effect = requests.exceptions.Timeout("timed out")

        result = call_collector_api("/status")

        assert result["success"] is False
        assert result["error"] == "Cannot connect to collector service"
        assert "details" not in result
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("core.routes.api.collection.utils.COLLECTOR_SERVICE_URL", "https://test:8545")
    @patch("core.routes.api.collection.utils.time.sleep")
    @patch("core.routes.api.collection.utils.requests.post")
    def test_post_timeout_is_not_retried(self, mock_post, mock_sleep):
        from core.routes.api.collection.utils import call_collector_api

        mock_post.side_effect = requests.exceptions.Timeout("timed out")

        result = call_collector_api("/api/force-collection/REGTECH", method="POST")

        assert result["success"] is False
        assert result["error"] == "Cannot connect to collector service"
        assert mock_post.call_count == 1
        mock_sleep.assert_not_called()

    @patch("core.routes.api.collection.utils.COLLECTOR_SERVICE_URL", "https://test:8545")
    @patch("core.routes.api.collection.utils.time.sleep")
    @patch("core.routes.api.collection.utils.requests.get")
    def test_retry_backoff_uses_exponential_delays(self, mock_get, mock_sleep):
        from core.routes.api.collection.utils import call_collector_api

        mock_get.side_effect = requests.exceptions.Timeout("timed out")

        call_collector_api("/health")

        assert mock_sleep.call_args_list == [call(1.0), call(2.0)]

    @patch("core.routes.api.collection.utils.COLLECTOR_SERVICE_URL", "https://test:8545")
    @patch("core.routes.api.collection.utils.time.sleep")
    @patch("core.routes.api.collection.utils.requests.get")
    def test_success_on_second_attempt_after_connection_error(self, mock_get, mock_sleep):
        from core.routes.api.collection.utils import call_collector_api

        success_response = _mock_response(status_code=200, json_data={"status": "ok"})
        mock_get.side_effect = [requests.exceptions.ConnectionError("temp error"), success_response]

        result = call_collector_api("/health")

        assert result == {"status": "ok"}
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(1.0)

    @patch("core.routes.api.collection.utils.COLLECTOR_SERVICE_URL", "https://test:8545")
    @patch("core.routes.api.collection.utils.requests.get")
    def test_generic_exception_returns_error(self, mock_get):
        from core.routes.api.collection.utils import call_collector_api

        mock_get.side_effect = RuntimeError("boom")

        result = call_collector_api("/health")

        assert result == {"success": False, "error": "Collector request failed"}
