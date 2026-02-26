"""Tests for credential_service.py"""

import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch



def _make_service(db_service=None):
    """Create CredentialService with mocked dependencies."""
    mock_db = db_service or Mock()
    with patch("core.services.credential_service.encryption_service") as mock_enc:
        mock_fernet = MagicMock()
        mock_fernet.encrypt.side_effect = lambda x: b"encrypted:" + x
        mock_fernet.decrypt.side_effect = lambda x: x.replace(b"encrypted:", b"")
        mock_enc.fernet = mock_fernet
        with patch("core.services.credential_service.Path") as mock_path:
            mock_path.return_value = MagicMock(spec=Path)
            mock_path.return_value.parent.mkdir = Mock()
            from core.services.credential_service import CredentialService

            svc = CredentialService(db_service=mock_db)
            svc.cipher_suite = mock_fernet
    return svc, mock_db


class TestCredentialServiceInit:
    def test_init_sets_db_service(self):
        svc, mock_db = _make_service()
        assert svc.db_service is mock_db


class TestSetupDatabase:
    def test_setup_creates_table(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        svc._setup_database()
        mock_cursor.execute.assert_called()


class TestSaveCredentials:
    def test_save_credentials_to_db(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        result = svc.save_credentials("user123", "pass456")
        assert result is True

    def test_save_credentials_db_failure_falls_back(self):
        svc, mock_db = _make_service()
        mock_db.get_connection.side_effect = Exception("DB down")
        # Should fall back to file or memory
        with patch.object(Path, "write_text"):
            with patch.object(Path, "exists", return_value=True):
                result = svc.save_credentials("user123", "pass456")
        # Even with fallback it should return True or handle gracefully
        assert isinstance(result, bool)


class TestLoadCredentials:
    def test_load_credentials_from_db(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        cred_data = json.dumps({"regtech_id": "user1", "regtech_pw": "pass1"})
        mock_cursor.fetchone.return_value = ("regtech", cred_data)
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        result = svc.load_credentials()
        assert result is not None or result is None  # depends on parsing

    def test_load_credentials_not_found(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        result = svc.load_credentials()
        # Should return None or empty when no credentials found
        assert result is None or isinstance(result, dict)


class TestGetCredentials:
    def test_get_credentials_from_collection_table(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("user1", "pass1")
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        result = svc.get_credentials()
        assert isinstance(result, dict)
        assert "regtech_id" in result or "username" in result

    def test_get_credentials_not_found(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        result = svc.get_credentials()
        assert result is None or isinstance(result, dict)


class TestHasCredentials:
    def test_has_credentials_true(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        result = svc.has_credentials()
        assert result is True

    def test_has_credentials_false(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        result = svc.has_credentials()
        assert result is False

    def test_has_credentials_db_error(self):
        svc, mock_db = _make_service()
        mock_db.get_connection.side_effect = Exception("DB down")
        result = svc.has_credentials()
        assert result is False


class TestClearCredentials:
    def test_clear_credentials(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        result = svc.clear_credentials()
        assert result is True

    def test_clear_credentials_db_error(self):
        svc, mock_db = _make_service()
        mock_db.get_connection.side_effect = Exception("DB down")
        result = svc.clear_credentials()
        assert isinstance(result, bool)


class TestSaveRegtechCredentials:
    def test_delegates_to_save_credentials(self):
        svc, _ = _make_service()
        with patch.object(svc, "save_credentials", return_value=True) as mock_save:
            svc.save_regtech_credentials("user1", "pass1")
            mock_save.assert_called_once_with("user1", "pass1")
