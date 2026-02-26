"""Unit tests for SettingsService"""

import pytest
from unittest.mock import Mock, patch
import os
import hashlib
import base64
from datetime import datetime, timedelta


def _make_fernet_key(seed: str = "test-secret") -> str:
    """Generate a valid Fernet key from a seed string."""
    return base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest()).decode()


@pytest.mark.unit
class TestSettingsService:
    """Tests for SettingsService"""

    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock()
        fernet_key = _make_fernet_key()
        with patch.dict(os.environ, {"SETTINGS_ENCRYPTION_KEY": fernet_key}):
            from app.core.services.settings_service import SettingsService

            self.service = SettingsService(db_service=self.mock_db)

    # --- Encryption ---

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypt then decrypt returns original value"""
        original = "my-secret-value"
        encrypted = self.service._encrypt_value(original)
        decrypted = self.service._decrypt_value(encrypted)
        assert decrypted == original

    def test_encrypt_produces_different_output(self):
        """Encryption produces ciphertext different from plaintext"""
        original = "my-secret-value"
        encrypted = self.service._encrypt_value(original)
        assert encrypted != original

    def test_decrypt_invalid_data_raises(self):
        """Decrypting invalid data raises InvalidToken (caught by caller)"""
        from cryptography.fernet import InvalidToken

        with pytest.raises((InvalidToken, Exception)):
            self.service._decrypt_value("not-valid-encrypted-data")

    # --- Cache ---

    def test_invalidate_cache(self):
        """Invalidate cache clears dict and timestamp"""
        self.service._cache = {"key": "val"}
        self.service._cache_timestamp = datetime.now()

        self.service._invalidate_cache()

        assert self.service._cache == {}
        assert self.service._cache_timestamp is None

    def test_is_cache_valid_when_empty(self):
        """Cache is invalid when empty"""
        self.service._cache_timestamp = None
        assert self.service._is_cache_valid() is False

    def test_is_cache_valid_when_fresh(self):
        """Cache is valid when recently set"""
        self.service._cache_timestamp = datetime.now()
        assert self.service._is_cache_valid() is True

    def test_is_cache_valid_when_expired(self):
        """Cache is invalid when expired"""
        self.service._cache_timestamp = datetime.now() - timedelta(seconds=120)
        self.service._cache_ttl = 60
        assert self.service._is_cache_valid() is False

    # --- _convert_value ---

    def test_convert_value_integer(self):
        assert self.service._convert_value("42", "integer") == 42

    def test_convert_value_boolean_true(self):
        assert self.service._convert_value("true", "boolean") is True
        assert self.service._convert_value("1", "boolean") is True
        assert self.service._convert_value("yes", "boolean") is True
        assert self.service._convert_value("on", "boolean") is True

    def test_convert_value_boolean_false(self):
        assert self.service._convert_value("false", "boolean") is False
        assert self.service._convert_value("0", "boolean") is False
        assert self.service._convert_value("no", "boolean") is False

    def test_convert_value_json(self):
        result = self.service._convert_value('{"key": "val"}', "json")
        assert result == {"key": "val"}

    def test_convert_value_json_invalid(self):
        """Invalid JSON returns original string"""
        result = self.service._convert_value("not-json", "json")
        assert result == "not-json"

    def test_convert_value_string_default(self):
        assert self.service._convert_value("hello", "string") == "hello"

    def test_convert_value_unknown_type(self):
        """Unknown type returns as string"""
        assert self.service._convert_value("hello", "custom") == "hello"

    # --- get_setting ---

    def test_get_setting_from_cache(self):
        """Cached setting returned without DB query"""
        self.service._cache = {"my_key": "cached_value"}
        self.service._cache_timestamp = datetime.now()

        result = self.service.get_setting("my_key")

        assert result == "cached_value"

    def test_get_setting_from_db(self):
        """Setting fetched from DB when cache invalid"""
        self.service._cache_timestamp = None

        # Cursor returns TUPLE: (value, setting_type, is_encrypted)
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ("db_value", "string", False)
        self.mock_db.get_connection.return_value = mock_conn

        result = self.service.get_setting("my_key")

        assert result == "db_value"

    def test_get_setting_returns_default_when_not_found(self):
        """Returns default when key not in DB"""
        self.service._cache_timestamp = None

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        self.mock_db.get_connection.return_value = mock_conn

        result = self.service.get_setting("missing_key", default="fallback")

        assert result == "fallback"

    def test_get_setting_decrypts_encrypted_value(self):
        """Encrypted value is decrypted before return"""
        encrypted = self.service._encrypt_value("secret")
        self.service._cache_timestamp = None

        # Cursor returns TUPLE: (value, setting_type, is_encrypted)
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (encrypted, "string", True)
        self.mock_db.get_connection.return_value = mock_conn

        result = self.service.get_setting("secret_key")

        assert result == "secret"

    def test_get_setting_db_error_returns_default(self):
        """DB error returns default value"""
        self.service._cache_timestamp = None
        self.mock_db.get_connection.side_effect = Exception("DB down")

        result = self.service.get_setting("key", default="safe")

        assert result == "safe"

    # --- set_setting ---

    def test_set_setting_success(self):
        """Setting saved successfully"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"id": 1}
        self.mock_db.get_connection.return_value = mock_conn

        result = self.service.set_setting("my_key", "my_value")

        assert result is True

    def test_set_setting_invalidates_cache(self):
        """Setting cache is invalidated after set"""
        self.service._cache = {"key": "old"}
        self.service._cache_timestamp = datetime.now()

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"id": 1}
        self.mock_db.get_connection.return_value = mock_conn

        self.service.set_setting("key", "new")

        assert self.service._cache == {}
        assert self.service._cache_timestamp is None

    def test_set_setting_not_found(self):
        """Set setting returns False when key not found"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        self.mock_db.get_connection.return_value = mock_conn

        result = self.service.set_setting("missing_key", "value")

        assert result is False

    def test_set_setting_db_error(self):
        """DB error returns False"""
        self.mock_db.get_connection.side_effect = Exception("Write failed")

        result = self.service.set_setting("key", "val")

        assert result is False

    # --- get_all_settings ---

    def test_get_all_settings_success(self):
        """All settings returned"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        # Cursor returns TUPLES: (key, value, type, description, is_encrypted, is_active, category, display_order, updated_at)
        mock_cursor.fetchall.return_value = [
            ("key1", "val1", "string", "Key 1", False, True, "general", 0, None),
        ]
        self.mock_db.get_connection.return_value = mock_conn

        result = self.service.get_all_settings()

        assert len(result) >= 1

    def test_get_all_settings_masks_encrypted(self):
        """Encrypted values masked when include_encrypted=False"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        # Cursor returns TUPLES: (key, value, type, description, is_encrypted, is_active, category, display_order, updated_at)
        mock_cursor.fetchall.return_value = [
            ("secret", "enc123", "string", "Secret", True, True, "security", 0, None),
        ]
        self.mock_db.get_connection.return_value = mock_conn

        result = self.service.get_all_settings(include_encrypted=False)

        assert any(r.get("value") == "********" or r.get("setting_value") == "********" for r in result)

    def test_get_all_settings_with_category_filter(self):
        """Category filter applied"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        self.mock_db.get_connection.return_value = mock_conn

        self.service.get_all_settings(category="security")

        # Verify cursor.execute was called
        mock_cursor.execute.assert_called_once()

    # --- Convenience methods ---

    def test_get_collection_interval_default(self):
        """Default collection interval is 3600"""
        self.service._cache_timestamp = None
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        self.mock_db.get_connection.return_value = mock_conn

        result = self.service.get_collection_interval()

        assert result == 3600

    def test_is_auto_collection_disabled_default(self):
        """Default auto collection disabled is True"""
        self.service._cache_timestamp = None
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        self.mock_db.get_connection.return_value = mock_conn

        result = self.service.is_auto_collection_disabled()

        assert result is True

    # --- create_setting ---

    def test_create_setting_success(self):
        """New setting created"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"id": 1}
        self.mock_db.get_connection.return_value = mock_conn

        result = self.service.create_setting(
            key="new_key", value="new_val", setting_type="string", description="A new setting"
        )

        assert result is True

    def test_create_setting_db_error(self):
        """Create failure returns False"""
        self.mock_db.get_connection.side_effect = Exception("Duplicate")

        result = self.service.create_setting(key="dup", value="val")

        assert result is False

    # --- delete_setting ---

    def test_delete_setting_success(self):
        """Setting soft-deleted"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"id": 1}
        self.mock_db.get_connection.return_value = mock_conn

        result = self.service.delete_setting("old_key")

        assert result is True

    def test_delete_setting_not_found(self):
        """Delete non-existent key returns False"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        self.mock_db.get_connection.return_value = mock_conn

        result = self.service.delete_setting("missing")

        assert result is False
