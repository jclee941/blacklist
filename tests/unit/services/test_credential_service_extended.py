"""Extended tests for credential_service uncovered methods."""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from core.services.credential_service import CredentialService


class TestCredentialServiceExtended:
    def _make_service(self):
        mock_db = Mock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        svc = CredentialService(db_service=mock_db)
        return svc, mock_db, mock_conn, mock_cursor

    def test_ensure_table_no_db(self):
        svc = CredentialService(db_service=None)
        svc._ensure_table()

    def test_ensure_table_success(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        svc._ensure_table()
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()

    def test_ensure_table_exception(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.execute.side_effect = Exception("table error")
        svc._ensure_table()

    def test_save_credentials_db_success_file_backup(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        with patch("builtins.open", mock_open()):
            result = svc.save_credentials("user", "pass")
        assert result is True
        mock_conn.commit.assert_called()

    def test_save_credentials_db_fail_file_fallback(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.execute.side_effect = Exception("DB error")
        with patch("builtins.open", mock_open()):
            result = svc.save_credentials("user", "pass")
        assert result is True

    def test_save_credentials_all_fail_memory(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.execute.side_effect = Exception("DB error")
        with patch("builtins.open", side_effect=IOError("no file")):
            result = svc.save_credentials("user", "pass")
        assert result is True

    def test_load_credentials_from_db(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        cred_json = json.dumps({"regtech_id": "user", "regtech_pw": "pass"})
        # fetchone returns 2-tuple: (encrypted_data, updated_at)
        mock_cursor.fetchone.return_value = (cred_json, "2024-01-01 00:00:00")
        result = svc.load_credentials()
        assert result is not None
        assert result["regtech_id"] == "user"

    def test_load_credentials_db_fail_file_fallback(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.execute.side_effect = Exception("DB error")
        file_data = json.dumps({"regtech_id": "fileuser", "regtech_pw": "filepass"})
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=file_data.encode())):
                result = svc.load_credentials()

    def test_load_credentials_not_found(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.fetchone.return_value = None
        with patch("os.path.exists", return_value=False):
            result = svc.load_credentials()

    def test_get_credentials_from_collection_table(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.fetchone.return_value = ("user123", "pass456")
        result = svc.get_credentials()
        assert result.get("regtech_id") == "user123"

    def test_get_credentials_not_found_fallback(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.fetchone.return_value = None
        result = svc.get_credentials()
        assert result == {}

    def test_get_credentials_empty_when_all_fail(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.fetchone.return_value = None
        with patch.object(svc, "load_credentials", return_value=None):
            result = svc.get_credentials()
        assert result == {} or result is None

    def test_has_credentials_true(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.fetchone.return_value = (1,)
        result = svc.has_credentials()
        assert result is True

    def test_has_credentials_false(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.fetchone.return_value = (0,)
        result = svc.has_credentials()
        assert result is False

    def test_clear_credentials_success(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.rowcount = 1
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.unlink"):
                result = svc.clear_credentials()
        assert result is True
        mock_conn.commit.assert_called()

    def test_clear_credentials_db_error(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.execute.side_effect = Exception("DB error")
        result = svc.clear_credentials()
        assert result is False
