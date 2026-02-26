"""Tests for regtech_config_service.py"""

import os
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch


def _make_service():
    from core.services.regtech_config_service import RegtechConfigService

    svc = RegtechConfigService()
    return svc


def _mock_secure_module():
    """Create a mock for the secure_credential_service module.

    RegtechConfigService imports from core.services.secure_credential_service
    INSIDE method bodies:
      from .secure_credential_service import secure_credential_service
      from .secure_credential_service import get_regtech_credentials
      from .secure_credential_service import delete_regtech_credentials

    Since secure_credential_service is a LocalProxy (requires Flask context),
    we replace the entire module in sys.modules with a mock.
    """
    mock_module = MagicMock()
    mock_module.secure_credential_service = MagicMock()
    mock_module.get_regtech_credentials = MagicMock()
    mock_module.delete_regtech_credentials = MagicMock()
    return mock_module


class TestRegtechConfigServiceInit:
    def test_init_sets_service_name(self):
        svc = _make_service()
        assert svc.service_name == "REGTECH"


class TestGetDefaultConfig:
    def test_returns_dict_with_expected_keys(self):
        svc = _make_service()
        config = svc._get_default_config()
        assert isinstance(config, dict)
        assert "base_url" in config or "timeout_seconds" in config


class TestSaveRegtechCredentials:
    def test_save_credentials_success(self):
        from flask import Flask

        app = Flask(__name__)
        mock_secure_svc = MagicMock()
        mock_secure_svc.save_credentials.return_value = True
        app.extensions["secure_credential_service"] = mock_secure_svc
        svc = _make_service()
        with app.app_context():
            result = svc.save_regtech_credentials(
                username="user1",
                password="pass1",
                base_url="https://regtech.fsec.or.kr",
                login_url="/login",
                advisory_url="/advisory",
            )
        assert isinstance(result, dict)
        mock_secure_svc.save_credentials.assert_called_once()

    def test_save_credentials_failure(self):
        from flask import Flask

        app = Flask(__name__)
        mock_secure_svc = MagicMock()
        mock_secure_svc.save_credentials.side_effect = Exception("DB error")
        app.extensions["secure_credential_service"] = mock_secure_svc
        svc = _make_service()
        with app.app_context():
            result = svc.save_regtech_credentials(
                username="user1",
                password="pass1",
                base_url="https://regtech.fsec.or.kr",
                login_url="/login",
                advisory_url="/advisory",
            )
        assert isinstance(result, dict)
        assert result.get("success") is False


class TestGetRegtechCredentials:
    def test_get_credentials_found(self):
        svc = _make_service()
        mock_mod = _mock_secure_module()
        mock_mod.get_regtech_credentials.return_value = {
            "username": "user1",
            "password": "pass1",
            "config": {"base_url": "https://example.com"},
        }
        with patch.dict("sys.modules", {"core.services.secure_credential_service": mock_mod}):
            result = svc.get_regtech_credentials()
        assert result is not None
        assert isinstance(result, dict)

    def test_get_credentials_not_found(self):
        svc = _make_service()
        mock_mod = _mock_secure_module()
        mock_mod.get_regtech_credentials.return_value = None
        with patch.dict("sys.modules", {"core.services.secure_credential_service": mock_mod}):
            result = svc.get_regtech_credentials()
        assert result is None


class TestTestRegtechConnection:
    def test_connection_no_credentials(self):
        svc = _make_service()
        mock_mod = _mock_secure_module()
        mock_mod.get_regtech_credentials.return_value = None
        with patch.dict("sys.modules", {"core.services.secure_credential_service": mock_mod}):
            result = svc.test_regtech_connection_enhanced()
        assert isinstance(result, dict)
        assert result.get("success") is False

    @patch("core.services.regtech_config_service.requests")
    def test_connection_with_credentials(self, mock_requests):
        svc = _make_service()
        mock_mod = _mock_secure_module()
        mock_mod.get_regtech_credentials.return_value = {
            "username": "user1",
            "password": "pass1",
            "config": {"base_url": "https://example.com"},
        }
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "healthy"}
        mock_requests.get.return_value = mock_resp
        with patch.dict("sys.modules", {"core.services.secure_credential_service": mock_mod}):
            result = svc.test_regtech_connection_enhanced()
        assert isinstance(result, dict)


class TestUpdateRegtechPassword:
    def test_update_password_no_existing(self):
        svc = _make_service()
        with patch.object(svc, "get_regtech_credentials", return_value=None):
            result = svc.update_regtech_password("new_pass")
        assert result is False

    def test_update_password_success(self):
        svc = _make_service()
        existing = {
            "username": "user1",
            "password": "old_pass",
            "config": {},
        }
        with patch.object(svc, "get_regtech_credentials", return_value=existing):
            with patch.object(svc, "save_regtech_credentials", return_value={"success": True}):
                result = svc.update_regtech_password("new_pass")
        assert isinstance(result, bool)


class TestInitializeRegtechCredentials:
    @patch.dict(os.environ, {"REGTECH_ID": "env_user", "REGTECH_PW": "env_pass"})
    def test_initialize_from_env(self):
        svc = _make_service()
        with patch.object(svc, "save_regtech_credentials", return_value={"success": True}):
            result = svc.initialize_regtech_credentials()
        assert result is True

    @patch.dict(os.environ, {}, clear=False)
    def test_initialize_no_env_vars(self):
        svc = _make_service()
        env_clean = {k: v for k, v in os.environ.items() if k not in ("REGTECH_ID", "REGTECH_PW")}
        with patch.dict(os.environ, env_clean, clear=True):
            result = svc.initialize_regtech_credentials()
        assert result is False


class TestDeleteRegtechCredentials:
    def test_delete_success(self):
        svc = _make_service()
        mock_mod = _mock_secure_module()
        mock_mod.delete_regtech_credentials.return_value = True
        with patch.dict("sys.modules", {"core.services.secure_credential_service": mock_mod}):
            result = svc.delete_regtech_credentials()
        assert result is True

    def test_delete_failure(self):
        svc = _make_service()
        mock_mod = _mock_secure_module()
        mock_mod.delete_regtech_credentials.side_effect = Exception("error")
        with patch.dict("sys.modules", {"core.services.secure_credential_service": mock_mod}):
            result = svc.delete_regtech_credentials()
        assert result is False


class TestFormatTestResult:
    def test_format_result(self):
        svc = _make_service()
        # phases must be a dict: {name: {"status": "success"|"failed"|"error"}}
        phases = {
            "credential_check": {"status": "success", "message": "OK"},
            "collector_health": {"status": "success", "message": "Healthy"},
        }
        start_time = datetime.now()
        result = svc._format_test_result(True, phases, start_time, "SUCCESS")
        assert isinstance(result, dict)
        assert result.get("success") is True
        assert "phases" in result
        assert "duration" in result
        assert "summary" in result
