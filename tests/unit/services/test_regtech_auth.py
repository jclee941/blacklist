import time
from unittest.mock import Mock, MagicMock, patch



def _make_auth_manager():
    from core.services.collection.regtech_auth import REGTECHAuthManager

    mgr = REGTECHAuthManager()
    return mgr


class TestREGTECHAuthManagerInit:
    def test_init_sets_base_url(self):
        mgr = _make_auth_manager()
        assert "regtech" in mgr.base_url.lower()

    def test_init_no_cached_session(self):
        mgr = _make_auth_manager()
        assert mgr._cached_session is None
        assert mgr._session_expiry is None
        assert mgr._session_cookies is None
        assert mgr._authenticated_user is None


class TestSessionValidity:
    def test_invalid_when_no_session(self):
        mgr = _make_auth_manager()
        assert mgr._is_session_valid() is False

    def test_invalid_when_expired(self):
        mgr = _make_auth_manager()
        mgr._cached_session = Mock()
        mgr._session_expiry = time.time() - 100
        mgr._session_cookies = {"cookie": "value"}
        assert mgr._is_session_valid() is False

    def test_valid_when_not_expired(self):
        mgr = _make_auth_manager()
        mgr._cached_session = Mock()
        mgr._session_expiry = time.time() + 3600
        mgr._session_cookies = {"cookie": "value"}
        assert mgr._is_session_valid() is True

    def test_invalid_when_no_cookies(self):
        mgr = _make_auth_manager()
        mgr._cached_session = Mock()
        mgr._session_expiry = time.time() + 3600
        mgr._session_cookies = None
        assert mgr._is_session_valid() is False


class TestCacheSession:
    def test_cache_session_stores_values(self):
        mgr = _make_auth_manager()
        mock_session = Mock()
        # dict(session.cookies) requires cookies to support iteration
        # Use a real dict-like object that supports dict() conversion
        mock_session.cookies = {"sid": "abc"}
        mgr._cache_session(mock_session, "testuser")
        assert mgr._cached_session is mock_session
        assert mgr._session_expiry > time.time()
        assert mgr._session_cookies == {"sid": "abc"}
        assert mgr._authenticated_user == "testuser"


class TestClearCachedSession:
    def test_clear_resets_all(self):
        mgr = _make_auth_manager()
        mgr._cached_session = Mock()
        mgr._session_expiry = time.time() + 3600
        mgr._session_cookies = {"sid": "abc"}
        mgr._authenticated_user = "testuser"
        mgr._clear_cached_session()
        assert mgr._cached_session is None
        assert mgr._session_expiry is None
        assert mgr._session_cookies is None
        assert mgr._authenticated_user is None


class TestTestRegtechLogin:
    @patch("core.services.collection.regtech_auth.requests")
    def test_login_success(self, mock_requests):
        mgr = _make_auth_manager()
        mock_session = MagicMock()
        mock_requests.Session.return_value = mock_session
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.cookies = MagicMock()
        mock_resp.cookies.__len__ = Mock(return_value=2)
        mock_resp.cookies.get_dict.return_value = {"JSESSIONID": "abc123"}
        mock_session.get.return_value = Mock(status_code=200)
        mock_session.post.return_value = mock_resp
        result = mgr.test_regtech_login("user1", "pass1")
        assert isinstance(result, dict)
        assert "success" in result

    @patch("core.services.collection.regtech_auth.requests")
    def test_login_connection_error(self, mock_requests):
        # Preserve real exception classes so `except requests.exceptions.Timeout` works
        import requests as real_requests

        mock_requests.exceptions = real_requests.exceptions
        mgr = _make_auth_manager()
        mock_session = Mock()
        mock_session.get.side_effect = real_requests.ConnectionError("connection refused")
        mock_requests.Session.return_value = mock_session
        result = mgr.test_regtech_login("user1", "pass1")
        assert isinstance(result, dict)
        assert result.get("success") is False


class TestGetCachedSession:
    def test_returns_cached_if_valid(self):
        mgr = _make_auth_manager()
        mock_session = Mock()
        mgr._cached_session = mock_session
        mgr._session_expiry = time.time() + 3600
        mgr._session_cookies = {"sid": "abc"}
        mgr._authenticated_user = "user1"
        session, msg = mgr.get_cached_session("user1", "pass1")
        assert session is mock_session

    @patch.object(
        __import__("core.services.collection.regtech_auth", fromlist=["REGTECHAuthManager"]).REGTECHAuthManager,
        "authenticate_session",
    )
    def test_creates_new_if_expired(self, mock_auth):
        mgr = _make_auth_manager()
        mgr._cached_session = None
        new_session = Mock()
        mock_auth.return_value = (new_session, "authenticated")
        session, msg = mgr.get_cached_session("user1", "pass1")
        assert session is new_session or mock_auth.called
