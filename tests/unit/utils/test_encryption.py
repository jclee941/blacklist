"""Unit tests for core.utils.encryption."""


import pytest

from core.utils.encryption import CredentialEncryption, EncryptionError


def _make_service(master_key="test-master-key-for-unit-tests"):
    """Create a CredentialEncryption instance with a test key."""
    return CredentialEncryption(master_key=master_key)


class TestCredentialEncryptionInit:
    """Tests for CredentialEncryption initialization."""

    def test_init_with_explicit_key(self):
        service = _make_service()
        assert service is not None

    def test_init_creates_fernet(self):
        service = _make_service()
        assert service.fernet is not None


class TestEncryptDecrypt:
    """Tests for encrypt/decrypt round-trip."""

    def test_encrypt_returns_string(self):
        service = _make_service()
        result = service.encrypt("hello world")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_decrypt_returns_original(self):
        service = _make_service()
        original = "sensitive-password-123!"
        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_empty_string_returns_empty(self):
        service = _make_service()
        assert service.encrypt("") == ""

    def test_decrypt_empty_string_returns_empty(self):
        service = _make_service()
        assert service.decrypt("") == ""

    def test_encrypted_differs_from_plaintext(self):
        service = _make_service()
        plaintext = "my-password"
        encrypted = service.encrypt(plaintext)
        assert encrypted != plaintext

    def test_different_keys_produce_different_ciphertext(self):
        service1 = _make_service("key-one")
        service2 = _make_service("key-two")
        plaintext = "same-password"
        enc1 = service1.encrypt(plaintext)
        enc2 = service2.encrypt(plaintext)
        assert enc1 != enc2

    def test_decrypt_with_wrong_key_fails(self):
        service1 = _make_service("key-one")
        service2 = _make_service("key-two")
        encrypted = service1.encrypt("secret")
        with pytest.raises(Exception):
            service2.decrypt(encrypted)

    def test_unicode_encrypt_decrypt(self):
        service = _make_service()
        original = "한글 테스트 비밀번호 🔑"
        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)
        assert decrypted == original

    def test_long_string_encrypt_decrypt(self):
        service = _make_service()
        original = "a" * 10000
        encrypted = service.encrypt(original)
        decrypted = service.decrypt(encrypted)
        assert decrypted == original


class TestEncryptDecryptCredentials:
    """Tests for encrypt_credentials/decrypt_credentials."""

    def test_encrypt_credentials_returns_dict(self):
        service = _make_service()
        result = service.encrypt_credentials("admin", "password123")
        assert isinstance(result, dict)
        assert "username" in result
        assert "password" in result
        assert result["encrypted"] is True
        assert result["encryption_version"] == "1.0"

    def test_decrypt_credentials_round_trip(self):
        service = _make_service()
        encrypted = service.encrypt_credentials("admin", "secret-pw")
        decrypted = service.decrypt_credentials(encrypted)
        assert decrypted["username"] == "admin"
        assert decrypted["password"] == "secret-pw"

    def test_decrypt_unencrypted_credentials(self):
        """When encrypted=False, should return raw values."""
        service = _make_service()
        data = {"username": "admin", "password": "plain", "encrypted": False}
        result = service.decrypt_credentials(data)
        assert result["username"] == "admin"
        assert result["password"] == "plain"


class TestPasswordHashing:
    """Tests for create_password_hash and verify_password_hash."""

    def test_create_hash_returns_hex_string(self):
        service = _make_service()
        h = service.create_password_hash("my-password")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest

    def test_same_password_same_hash(self):
        service = _make_service()
        h1 = service.create_password_hash("password")
        h2 = service.create_password_hash("password")
        assert h1 == h2

    def test_different_password_different_hash(self):
        service = _make_service()
        h1 = service.create_password_hash("password1")
        h2 = service.create_password_hash("password2")
        assert h1 != h2

    def test_verify_correct_password(self):
        service = _make_service()
        h = service.create_password_hash("secret")
        assert service.verify_password_hash("secret", h) is True

    def test_verify_wrong_password(self):
        service = _make_service()
        h = service.create_password_hash("secret")
        assert service.verify_password_hash("wrong", h) is False


class TestEncryptionError:
    """Tests for EncryptionError exception."""

    def test_is_exception(self):
        assert issubclass(EncryptionError, Exception)

    def test_can_be_raised(self):
        with pytest.raises(EncryptionError):
            raise EncryptionError("encryption failed")
