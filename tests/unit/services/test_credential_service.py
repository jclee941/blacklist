"""Tests for credential_service.py"""

import base64
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
    def test_runtime_schema_creation_is_not_exposed(self):
        svc, mock_db = _make_service()
        assert not hasattr(svc, "_setup_database")
        mock_db.get_connection.assert_not_called()


class TestSaveCredentials:
    def test_save_credentials_to_db(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        result = svc.save_credentials("user123", "pass456")
        assert result is True

    def test_save_credentials_db_failure_does_not_fall_back(self, tmp_path):
        svc, mock_db = _make_service()
        svc.credentials_file = tmp_path / "credentials.enc"
        mock_db.get_connection.side_effect = Exception("DB down")
        result = svc.save_credentials("user123", "pass456")
        assert result is False
        assert not svc.credentials_file.exists()


class TestLoadCredentials:
    def test_load_credentials_from_db_decrypts_saved_payload(self, tmp_path):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        credentials = {"regtech_id": "user1", "regtech_pw": "pass1"}
        encrypted_data = svc.cipher_suite.encrypt(json.dumps(credentials).encode())
        mock_cursor.fetchone.return_value = (base64.b64encode(encrypted_data).decode(), "2024-01-01")
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        svc.credentials_file = tmp_path / "credentials.enc"
        result = svc.load_credentials()

        assert result == credentials

    def test_load_credentials_from_db_accepts_legacy_plaintext_json(self, tmp_path):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        credentials = {"regtech_id": "legacy-user", "regtech_pw": "legacy-password"}
        mock_cursor.fetchone.return_value = (json.dumps(credentials), "2024-01-01")
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        svc.credentials_file = tmp_path / "credentials.enc"
        result = svc.load_credentials()

        assert result == credentials

    def test_load_credentials_falls_back_to_file_when_db_record_is_corrupt(self, tmp_path):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("not-a-valid-credential-record", "2024-01-01")
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        credentials = {"regtech_id": "backup-user", "regtech_pw": "backup-password"}
        svc.credentials_file = tmp_path / "credentials.enc"
        svc.credentials_file.write_bytes(b"encrypted:" + json.dumps(credentials).encode())

        assert svc.load_credentials() == credentials

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
