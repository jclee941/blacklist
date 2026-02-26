"""Unit tests for core.exceptions module."""


from core.exceptions.base_exceptions import BlacklistError, APIError, ExternalAPIError
from core.exceptions.auth_exceptions import AuthenticationError, AuthorizationError


class TestBlacklistError:
    """Tests for BlacklistError base exception."""

    def test_message_preserved(self):
        err = BlacklistError("test error")
        assert err.message == "test error"

    def test_default_error_code(self):
        err = BlacklistError("test")
        assert err.error_code is not None

    def test_custom_error_code(self):
        err = BlacklistError("test", error_code="CUSTOM_CODE")
        assert err.error_code == "CUSTOM_CODE"

    def test_details_default_empty(self):
        err = BlacklistError("test")
        assert isinstance(err.details, dict)

    def test_details_custom(self):
        err = BlacklistError("test", details={"field": "ip"})
        assert err.details["field"] == "ip"

    def test_to_dict(self):
        err = BlacklistError("test error", error_code="TEST")
        d = err.to_dict()
        assert "error_type" in d
        assert "error_code" in d
        assert "message" in d

    def test_to_api_response(self):
        err = BlacklistError("test error", error_code="TEST")
        resp = err.to_api_response()
        assert "error" in resp or "error_code" in resp

    def test_with_cause(self):
        original = ValueError("original")
        err = BlacklistError("wrapped", cause=original)
        assert err.cause == original


class TestAPIError:
    """Tests for APIError exception."""

    def test_default_status_400(self):
        err = APIError("bad request")
        assert err.status_code == 400

    def test_custom_status(self):
        err = APIError("not found", status_code=404)
        assert err.status_code == 404

    def test_inherits_blacklist_error(self):
        assert issubclass(APIError, BlacklistError)

    def test_to_api_response_rfc7807(self):
        err = APIError("bad request", status_code=400, error_code="INVALID_IP")
        resp = err.to_api_response()
        assert isinstance(resp, dict)


class TestExternalAPIError:
    """Tests for ExternalAPIError exception."""

    def test_default_status_502(self):
        err = ExternalAPIError("gateway timeout", api_name="FortiManager")
        assert err.status_code == 502

    def test_inherits_status_code(self):
        """ExternalAPIError preserves custom status code."""
        err = ExternalAPIError("error", api_name="TestAPI", status_code=503)
        assert err.status_code == 503

    def test_inherits_api_error(self):
        assert issubclass(ExternalAPIError, APIError)


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_message(self):
        err = AuthenticationError("token expired")
        assert err.message == "token expired"

    def test_error_code(self):
        err = AuthenticationError("invalid")
        assert err.error_code == "AUTHENTICATION_ERROR"

    def test_inherits_blacklist_error(self):
        assert issubclass(AuthenticationError, BlacklistError)

    def test_with_auth_type(self):
        err = AuthenticationError("expired", auth_type="jwt")
        assert err.auth_type == "jwt"


class TestAuthorizationError:
    """Tests for AuthorizationError."""

    def test_message(self):
        err = AuthorizationError("insufficient permissions")
        assert err.message == "insufficient permissions"

    def test_error_code(self):
        err = AuthorizationError("denied")
        assert err.error_code == "AUTHORIZATION_ERROR"

    def test_inherits_blacklist_error(self):
        assert issubclass(AuthorizationError, BlacklistError)

    def test_with_required_role(self):
        err = AuthorizationError("denied", required_role="admin")
        assert err.required_role == "admin"

    def test_with_resource(self):
        err = AuthorizationError("denied", resource="/admin/settings")
        assert err.resource == "/admin/settings"
