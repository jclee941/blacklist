"""Extended tests for core.utils.encryption"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from core.utils.encryption import CredentialEncryption, EncryptionError


class TestCredentialEncryptionExtended:
    def _make_encryption(self):
        return CredentialEncryption(master_key=b"test-master-key-for-testing-1234")

    def test_encrypt_empty_string(self):
        enc = self._make_encryption()
        result = enc.encrypt("")
        assert result == ""

    def test_decrypt_empty_string(self):
        enc = self._make_encryption()
        result = enc.decrypt("")
        assert result == ""

    def test_encrypt_decrypt_roundtrip(self):
        enc = self._make_encryption()
        original = "sensitive-data-12345"
        encrypted = enc.encrypt(original)
        assert encrypted != original
        assert encrypted != ""
        decrypted = enc.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_credentials(self):
        enc = self._make_encryption()
        result = enc.encrypt_credentials("myuser", "mypass")
        assert result["encrypted"] is True
        assert result["encryption_version"] == "1.0"
        assert result["username"] != "myuser"
        assert result["password"] != "mypass"

    def test_decrypt_credentials(self):
        enc = self._make_encryption()
        encrypted = enc.encrypt_credentials("myuser", "mypass")
        decrypted = enc.decrypt_credentials(encrypted)
        assert decrypted["username"] == "myuser"
        assert decrypted["password"] == "mypass"

    def test_decrypt_credentials_unencrypted(self):
        enc = self._make_encryption()
        data = {"username": "plain", "password": "text", "encrypted": False}
        result = enc.decrypt_credentials(data)
        assert result["username"] == "plain"

    def test_decrypt_credentials_no_flag(self):
        enc = self._make_encryption()
        data = {"username": "plain", "password": "text"}
        result = enc.decrypt_credentials(data)
        assert result["username"] == "plain"

    def test_create_password_hash(self):
        enc = self._make_encryption()
        hash1 = enc.create_password_hash("mypassword")
        hash2 = enc.create_password_hash("mypassword")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_verify_password_hash(self):
        enc = self._make_encryption()
        hash_val = enc.create_password_hash("mypassword")
        assert enc.verify_password_hash("mypassword", hash_val) is True
        assert enc.verify_password_hash("wrong", hash_val) is False

    def test_create_password_hash_different_passwords(self):
        enc = self._make_encryption()
        h1 = enc.create_password_hash("password1")
        h2 = enc.create_password_hash("password2")
        assert h1 != h2

    def test_get_or_create_master_key_from_env(self):
        with patch.dict("os.environ", {"CREDENTIAL_MASTER_KEY": "env-key-1234"}):
            with patch("os.path.exists", return_value=False):
                enc = CredentialEncryption()
                assert enc.master_key is not None

    def test_encrypt_special_characters(self):
        enc = self._make_encryption()
        original = "한국어 테스트 !@#$%^&*() \n\t"
        encrypted = enc.encrypt(original)
        decrypted = enc.decrypt(encrypted)
        assert decrypted == original

    def test_decrypt_invalid_data(self):
        enc = self._make_encryption()
        with pytest.raises(EncryptionError):
            enc.decrypt("not-valid-encrypted-data")

    def test_encrypt_long_string(self):
        enc = self._make_encryption()
        original = "A" * 10000
        encrypted = enc.encrypt(original)
        decrypted = enc.decrypt(encrypted)
        assert decrypted == original
