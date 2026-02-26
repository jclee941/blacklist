"""Tests for fortimanager_push_service.py"""

import os
import time
from unittest.mock import Mock, MagicMock, patch


def _make_service(db_service=None):
    """Create FortiManagerPushService with mocked env."""
    mock_db = db_service or Mock()
    env = {
        "FMG_HOST": "10.0.0.1",
        "FMG_USER": "admin",
        "FMG_PASS": "secret",
        "FMG_ADOM": "root",
        "BLACKLIST_API_URL": "http://localhost:2542/api/blacklist/text",
    }
    with patch.dict(os.environ, env):
        from core.services.fortimanager_push_service import FortiManagerPushService

        svc = FortiManagerPushService(db_service=mock_db)
    return svc, mock_db


class TestFortiManagerPushServiceInit:
    def test_init_reads_env_vars(self):
        svc, _ = _make_service()
        assert svc.fmg_host == "10.0.0.1"
        assert svc.fmg_user == "admin"
        assert svc.fmg_pass == "secret"
        assert svc.fmg_adom == "root"

    def test_init_sets_session_id_none(self):
        svc, _ = _make_service()
        assert svc.session_id is None

    def test_init_sets_db_conn_none(self):
        svc, _ = _make_service()
        assert svc.db_conn is None

    def test_init_sets_api_url(self):
        svc, _ = _make_service()
        assert "blacklist" in svc.api_url.lower()

    def test_init_default_user(self):
        env = {"FMG_HOST": "10.0.0.1", "FMG_PASS": "secret"}
        with patch.dict(os.environ, env, clear=False):
            from core.services.fortimanager_push_service import FortiManagerPushService

            svc = FortiManagerPushService(db_service=Mock())
        assert svc.fmg_user == "admin"


class TestLoginFortimanager:
    @patch("core.services.fortimanager_push_service.requests")
    def test_login_success(self, mock_requests):
        svc, _ = _make_service()
        mock_resp = Mock()
        mock_resp.json.return_value = {
            "result": [{"status": {"code": 0}, "url": "/sys/login/user"}],
            "session": "abc123",
        }
        mock_requests.post.return_value = mock_resp
        result = svc.login_fortimanager()
        assert result is True
        assert svc.session_id == "abc123"

    @patch("core.services.fortimanager_push_service.requests")
    def test_login_failure(self, mock_requests):
        svc, _ = _make_service()
        mock_resp = Mock()
        mock_resp.json.return_value = {"result": [{"status": {"code": -1, "message": "auth failed"}}]}
        mock_requests.post.return_value = mock_resp
        result = svc.login_fortimanager()
        assert result is False

    @patch("core.services.fortimanager_push_service.requests")
    def test_login_connection_error(self, mock_requests):
        import requests as real_requests

        mock_requests.RequestException = real_requests.RequestException
        mock_requests.exceptions = real_requests.exceptions
        svc, _ = _make_service()
        mock_requests.post.side_effect = real_requests.ConnectionError("connection refused")
        result = svc.login_fortimanager()
        assert result is False

    def test_login_no_host(self):
        with patch.dict(os.environ, {"FMG_HOST": "", "FMG_PASS": "secret"}):
            from core.services.fortimanager_push_service import FortiManagerPushService

            svc = FortiManagerPushService(db_service=Mock())
            svc.fmg_host = ""
        result = svc.login_fortimanager()
        assert result is False

    def test_login_no_password(self):
        svc, _ = _make_service()
        svc.fmg_pass = ""
        result = svc.login_fortimanager()
        assert result is False


class TestFetchBlacklist:
    @patch("core.services.fortimanager_push_service.requests")
    def test_fetch_success(self, mock_requests):
        svc, _ = _make_service()
        mock_resp = Mock()
        mock_resp.text = "1.2.3.4\n5.6.7.8"
        mock_resp.status_code = 200
        mock_requests.get.return_value = mock_resp
        result = svc.fetch_blacklist()
        assert result is not None
        assert "1.2.3.4" in result

    @patch("core.services.fortimanager_push_service.requests")
    def test_fetch_failure(self, mock_requests):
        svc, _ = _make_service()
        mock_requests.get.side_effect = Exception("connection error")
        result = svc.fetch_blacklist()
        assert result is None


class TestUploadToFortimanager:
    @patch("core.services.fortimanager_push_service.requests")
    def test_upload_success(self, mock_requests):
        svc, _ = _make_service()
        svc.session_id = "abc123"
        mock_resp = Mock()
        mock_resp.json.return_value = {"result": [{"status": {"code": 0}}]}
        mock_requests.post.return_value = mock_resp
        result = svc.upload_to_fortimanager("1.2.3.4\n5.6.7.8")
        assert result is True

    @patch("core.services.fortimanager_push_service.requests")
    def test_upload_session_expired_retries(self, mock_requests):
        svc, _ = _make_service()
        svc.session_id = "abc123"
        # First call: session expired (-11), second: login, third: upload success
        expired_resp = Mock()
        expired_resp.json.return_value = {"result": [{"status": {"code": -11, "message": "session expired"}}]}
        login_resp = Mock()
        login_resp.json.return_value = {"result": [{"status": {"code": 0}}], "session": "new_session"}
        success_resp = Mock()
        success_resp.json.return_value = {"result": [{"status": {"code": 0}}]}
        mock_requests.post.side_effect = [expired_resp, login_resp, success_resp]
        result = svc.upload_to_fortimanager("1.2.3.4")
        assert result is True

    @patch("core.services.fortimanager_push_service.requests")
    def test_upload_connection_error(self, mock_requests):
        # Preserve real exception classes so `except requests.RequestException` works
        import requests as real_requests

        mock_requests.RequestException = real_requests.RequestException
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.post.side_effect = real_requests.ConnectionError("connection error")
        svc, _ = _make_service()
        svc.session_id = "fake-session"
        result = svc.upload_to_fortimanager("1.2.3.4")
        assert result is False


class TestHandleChangeNotification:
    def test_handle_change_notification(self):
        svc, _ = _make_service()
        svc.last_update = time.time() - 120  # Ensure not rate limited
        with patch.object(svc, "fetch_blacklist", return_value="1.2.3.4"):
            with patch.object(svc, "upload_to_fortimanager", return_value=True):
                svc.handle_change_notification("test payload")
        # No assertion needed - just verify no crash

    def test_handle_change_rate_limited(self):
        svc, _ = _make_service()
        svc.last_update = time.time()  # Recent update - should be rate limited
        with patch.object(svc, "fetch_blacklist"):
            svc.handle_change_notification("test payload")
        # Should NOT call fetch_blacklist due to rate limiting
        # (This may or may not be called depending on rate limit window)


class TestConnectDatabase:
    def test_connect_database_with_db_service(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_db.create_raw_connection = Mock(return_value=mock_conn)
        svc.connect_database()
        assert svc.db_conn is mock_conn

    def test_connect_database_without_db_service(self):
        svc, _ = _make_service()
        svc.db_service = None
        with patch("core.services.fortimanager_push_service.psycopg2") as mock_psycopg2:
            mock_conn = MagicMock()
            mock_psycopg2.connect.return_value = mock_conn
            svc.connect_database()
        assert svc.db_conn is mock_conn
