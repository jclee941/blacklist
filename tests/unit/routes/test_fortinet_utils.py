from unittest.mock import Mock, patch
from flask import Flask

from core.routes.api.fortinet.utils import _log_pull_request


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


class TestFortinetUtils:
    def test_log_pull_request_success_log(self):
        app = make_app()
        app.extensions["db_service"] = Mock()

        with app.test_request_context(
            "/api/fortinet/pull",
            headers={"X-Forwarded-For": "203.0.113.10", "User-Agent": "test-agent"},
            environ_base={"REMOTE_ADDR": "198.51.100.1"},
        ):
            _log_pull_request("/api/fortinet/pull", ip_count=12)

        app.extensions["db_service"].execute.assert_called_once()

    def test_log_pull_request_no_db_service_returns_early(self):
        app = make_app()

        with app.test_request_context("/api/fortinet/pull", environ_base={"REMOTE_ADDR": "198.51.100.1"}):
            _log_pull_request("/api/fortinet/pull", ip_count=1)

    def test_log_pull_request_db_service_none_returns_early(self):
        app = make_app()
        app.extensions["db_service"] = None

        with app.test_request_context("/api/fortinet/pull", environ_base={"REMOTE_ADDR": "198.51.100.1"}):
            _log_pull_request("/api/fortinet/pull", ip_count=1)

    def test_log_pull_request_x_forwarded_for_multiple_ips_uses_first(self):
        app = make_app()
        app.extensions["db_service"] = Mock()

        with app.test_request_context(
            "/api/fortinet/pull",
            headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.2", "User-Agent": "agent"},
            environ_base={"REMOTE_ADDR": "198.51.100.1"},
        ):
            _log_pull_request("/api/fortinet/pull", ip_count=8)

        _, params = app.extensions["db_service"].execute.call_args[0]
        assert params[0] == "10.0.0.1"

    def test_log_pull_request_no_x_forwarded_for_uses_remote_addr(self):
        app = make_app()
        app.extensions["db_service"] = Mock()

        with app.test_request_context(
            "/api/fortinet/pull",
            headers={"User-Agent": "agent"},
            environ_base={"REMOTE_ADDR": "198.51.100.99"},
        ):
            _log_pull_request("/api/fortinet/pull", ip_count=8)

        _, params = app.extensions["db_service"].execute.call_args[0]
        assert params[0] == "198.51.100.99"

    def test_log_pull_request_truncates_user_agent_to_500_chars(self):
        app = make_app()
        app.extensions["db_service"] = Mock()
        long_user_agent = "a" * 700

        with app.test_request_context(
            "/api/fortinet/pull",
            headers={"User-Agent": long_user_agent},
            environ_base={"REMOTE_ADDR": "198.51.100.99"},
        ):
            _log_pull_request("/api/fortinet/pull", ip_count=3)

        _, params = app.extensions["db_service"].execute.call_args[0]
        assert len(params[1]) == 500
        assert params[1] == long_user_agent[:500]

    def test_log_pull_request_db_exception_logs_warning_and_does_not_raise(self):
        app = make_app()
        db_service = Mock()
        db_service.execute.side_effect = RuntimeError("db down")
        app.extensions["db_service"] = db_service

        with patch("core.routes.api.fortinet.utils.logger.warning") as mock_warning:
            with app.test_request_context("/api/fortinet/pull", environ_base={"REMOTE_ADDR": "198.51.100.99"}):
                _log_pull_request("/api/fortinet/pull", ip_count=3)

        mock_warning.assert_called_once()
        assert "Failed to log pull request" in mock_warning.call_args[0][0]

    def test_log_pull_request_uses_correct_sql_params(self):
        app = make_app()
        app.extensions["db_service"] = Mock()

        with app.test_request_context(
            "/api/fortinet/pull",
            headers={"User-Agent": "ua"},
            environ_base={"REMOTE_ADDR": "203.0.113.9"},
        ):
            _log_pull_request("/api/fortinet/pull", ip_count=99, status_code=201, response_time_ms=345)

        sql, params = app.extensions["db_service"].execute.call_args[0]
        assert "INSERT INTO fortinet_pull_logs" in sql
        assert params == ("203.0.113.9", "ua", "/api/fortinet/pull", 99, 345, 201)
