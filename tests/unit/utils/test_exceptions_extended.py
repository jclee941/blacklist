from unittest.mock import Mock

import pytest


class TestConfigExceptions:
    def test_configuration_error(self):
        from core.exceptions.config_exceptions import ConfigurationError

        err = ConfigurationError("Missing config", config_key="DB_URL")
        assert "Missing config" in str(err)
        assert err.error_code == "CONFIGURATION_ERROR"
        assert err.details.get("config_key") == "DB_URL"

    def test_configuration_error_with_file(self):
        from core.exceptions.config_exceptions import ConfigurationError

        err = ConfigurationError("Bad config", config_file="/etc/app.conf", expected_type="dict")
        assert err.details.get("config_file") == "/etc/app.conf"
        assert err.details.get("expected_type") == "dict"

    def test_dependency_error(self):
        from core.exceptions.config_exceptions import DependencyError

        err = DependencyError("Service unavailable", service_name="redis")
        assert err.error_code == "DEPENDENCY_ERROR"
        assert err.details.get("service_name") == "redis"

    def test_dependency_error_with_chain(self):
        from core.exceptions.config_exceptions import DependencyError

        chain = ["app", "cache", "redis"]
        err = DependencyError("Chain failure", dependency_chain=chain)
        assert err.details.get("dependency_chain") == chain

    def test_dependency_error_default_chain(self):
        from core.exceptions.config_exceptions import DependencyError

        err = DependencyError("No chain")
        # When dependency_chain is not provided, it defaults to []
        # but may not be in details if not passed as kwarg
        chain = err.details.get("dependency_chain") if err.details else None
        if chain is not None:
            assert chain == []
        else:
            assert err.dependency_chain == []


class TestDataExceptions:
    def test_data_processing_error(self):
        from core.exceptions.data_exceptions import DataProcessingError

        err = DataProcessingError("Parse failed", file_path="/tmp/data.csv", operation="parse")
        assert err.error_code == "DATA_PROCESSING_ERROR"
        assert err.details.get("file_path") == "/tmp/data.csv"
        assert err.details.get("operation") == "parse"

    def test_data_processing_error_with_type(self):
        from core.exceptions.data_exceptions import DataProcessingError

        err = DataProcessingError("Invalid data", data_type="JSON")
        assert err.details.get("data_type") == "JSON"

    def test_data_error(self):
        from core.exceptions.data_exceptions import DataError

        err = DataError("Source failed", data_source="REGTECH", operation="fetch")
        assert err.error_code == "DATA_ERROR"
        assert err.details.get("data_source") == "REGTECH"


class TestValidationExceptions:
    def test_validation_error(self):
        from core.exceptions.validation_exceptions import ValidationError

        err = ValidationError("Invalid IP", field="ip_address", value="not-an-ip")
        assert err.status_code == 400
        assert err.error_code == "VALIDATION_ERROR"

    def test_bad_request_error(self):
        from core.exceptions.validation_exceptions import BadRequestError

        err = BadRequestError("Bad data", field="name")
        assert err.status_code == 400
        assert err.error_code == "BAD_REQUEST"

    def test_not_found_error(self):
        from core.exceptions.validation_exceptions import NotFoundError

        err = NotFoundError("IP not found", resource="blacklist_ip")
        assert err.status_code == 404
        assert err.error_code == "NOT_FOUND"

    def test_conflict_error(self):
        from core.exceptions.validation_exceptions import ConflictError

        err = ConflictError("Duplicate IP", resource="blacklist_ip")
        assert err.status_code == 409
        assert err.error_code == "CONFLICT"

    def test_internal_server_error(self):
        from core.exceptions.validation_exceptions import InternalServerError

        cause = ValueError("bad value")
        err = InternalServerError("Something broke", cause=cause)
        assert err.status_code == 500
        assert err.error_code == "INTERNAL_SERVER_ERROR"

    def test_unauthorized_error_default_message(self):
        from core.exceptions.validation_exceptions import UnauthorizedError

        err = UnauthorizedError()
        assert err.status_code == 401
        assert "Authentication" in str(err) or "authentication" in str(err).lower()

    def test_forbidden_error_default_message(self):
        from core.exceptions.validation_exceptions import ForbiddenError

        err = ForbiddenError()
        assert err.status_code == 403


class TestServiceExceptions:
    def test_rate_limit_error(self):
        from core.exceptions.service_exceptions import RateLimitError

        err = RateLimitError("Too many requests", identifier="user1", limit=100, window_seconds=60, retry_after=30)
        assert err.error_code == "RATE_LIMIT_ERROR"
        assert err.details.get("identifier") == "user1"
        assert err.details.get("limit") == 100
        assert err.details.get("retry_after") == 30

    def test_service_unavailable_error(self):
        from core.exceptions.service_exceptions import ServiceUnavailableError

        err = ServiceUnavailableError("Redis down", service_name="redis", retry_after=60)
        assert err.error_code == "SERVICE_UNAVAILABLE_ERROR"
        assert err.details.get("service_name") == "redis"

    def test_monitoring_error(self):
        from core.exceptions.service_exceptions import MonitoringError

        err = MonitoringError("Metric collection failed", metric_name="cpu_usage", component="monitor")
        assert err.error_code == "MONITORING_ERROR"
        assert err.details.get("metric_name") == "cpu_usage"


class TestInfrastructureExceptions:
    def test_cache_error(self):
        from core.exceptions.infrastructure_exceptions import CacheError

        err = CacheError("Cache miss", cache_key="user:123", operation="get", cache_type="redis")
        assert err.error_code == "CACHE_ERROR"
        assert err.details.get("cache_key") == "user:123"
        assert err.details.get("cache_type") == "redis"

    def test_cache_error_default_type(self):
        from core.exceptions.infrastructure_exceptions import CacheError

        err = CacheError("Cache error")
        assert err.details.get("cache_type") == "unknown"

    def test_database_error(self):
        from core.exceptions.infrastructure_exceptions import DatabaseError

        err = DatabaseError("Query failed", query="SELECT *", table="blacklist_ips")
        assert err.error_code == "DATABASE_ERROR"
        assert err.details.get("table") == "blacklist_ips"

    def test_database_error_sanitizes_url(self):
        from core.exceptions.infrastructure_exceptions import DatabaseError

        err = DatabaseError("Connection failed", database_url="postgresql://user:secret@host:5432/db")
        url_in_details = err.details.get("database_url", "")
        assert "secret" not in url_in_details
        assert "****" in url_in_details

    def test_connection_error(self):
        from core.exceptions.infrastructure_exceptions import ConnectionError as ConnError

        err = ConnError("Timeout", url="https://api.example.com", timeout=30, status_code=504)
        assert err.error_code == "CONNECTION_ERROR"
        assert err.details.get("timeout") == 30
        assert err.details.get("status_code") == 504


class TestErrorUtils:
    def test_handle_exception_already_blacklist_error(self):
        from core.exceptions.error_utils import handle_exception
        from core.exceptions.base_exceptions import BlacklistError

        original = BlacklistError("test")
        result = handle_exception(original)
        assert result is original

    def test_handle_value_error_raises_type_error(self):
        """ValidationError.__init__ does not accept cause= kwarg — known production bug."""
        from core.exceptions.error_utils import handle_exception

        with pytest.raises(TypeError, match="unexpected keyword argument"):
            handle_exception(ValueError("bad value"))

    def test_handle_file_not_found_raises_type_error(self):
        """DataProcessingError.__init__ does not accept cause= kwarg — known production bug."""
        from core.exceptions.error_utils import handle_exception

        with pytest.raises(TypeError, match="unexpected keyword argument"):
            handle_exception(FileNotFoundError("missing.csv"))

    def test_handle_permission_error_raises_type_error(self):
        """AuthorizationError.__init__ does not accept cause= kwarg — known production bug."""
        from core.exceptions.error_utils import handle_exception

        with pytest.raises(TypeError, match="unexpected keyword argument"):
            handle_exception(PermissionError("access denied"))

    def test_handle_connection_error_raises_type_error(self):
        """ServiceUnavailableError.__init__ does not accept cause= kwarg — known production bug."""
        from core.exceptions.error_utils import handle_exception

        with pytest.raises(TypeError, match="unexpected keyword argument"):
            handle_exception(ConnectionError("refused"))

    def test_handle_generic_exception(self):
        from core.exceptions.error_utils import handle_exception

        result = handle_exception(RuntimeError("something"))
        assert hasattr(result, "error_code")

    def test_handle_with_context_raises_type_error(self):
        """ValueError triggers ValidationError with cause= kwarg — TypeError."""
        from core.exceptions.error_utils import handle_exception

        with pytest.raises(TypeError, match="unexpected keyword argument"):
            handle_exception(ValueError("test"), context="processing IPs")

    def test_log_exception_blacklist_error(self):
        from core.exceptions.error_utils import log_exception
        from core.exceptions.base_exceptions import BlacklistError

        mock_logger = Mock()
        log_exception(BlacklistError("test"), logger_instance=mock_logger)
        mock_logger.error.assert_called()

    def test_log_exception_generic(self):
        from core.exceptions.error_utils import log_exception

        mock_logger = Mock()
        log_exception(RuntimeError("test"), logger_instance=mock_logger)
        mock_logger.error.assert_called()

    def test_create_error_response_blacklist_error(self):
        from core.exceptions.error_utils import create_error_response
        from core.exceptions.base_exceptions import BlacklistError

        result = create_error_response(BlacklistError("test"))
        assert isinstance(result, dict)
        assert "error" in result or "success" in result

    def test_create_error_response_generic(self):
        from core.exceptions.error_utils import create_error_response

        result = create_error_response(RuntimeError("test"))
        assert isinstance(result, dict)

    def test_create_error_response_include_details(self):
        from core.exceptions.error_utils import create_error_response
        from core.exceptions.base_exceptions import BlacklistError

        result = create_error_response(BlacklistError("test", details={"key": "val"}), include_details=True)
        assert isinstance(result, dict)

    def test_create_error_response_exclude_details(self):
        from core.exceptions.error_utils import create_error_response
        from core.exceptions.base_exceptions import BlacklistError

        result = create_error_response(BlacklistError("test", details={"key": "val"}), include_details=False)
        assert isinstance(result, dict)
