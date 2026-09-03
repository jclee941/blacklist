"""Unit tests for core.auth.jwt_service."""

from datetime import datetime, timedelta, timezone
from typing import final

import jwt
import pytest

from core.auth.jwt_service import JWTService, JWT_ALGORITHM, DEFAULT_TOKEN_EXPIRY_HOURS


class TestJWTServiceInit:
    """Tests for JWTService initialization."""

    def test_init_with_valid_key(self):
        service = JWTService(secret_key="my-secret-key-123")
        assert service._secret_key == "my-secret-key-123"

    def test_init_with_empty_string_raises(self):
        with pytest.raises(ValueError):
            JWTService(secret_key="")

    def test_init_with_none_raises(self):
        constructor = getattr(__import__("core.auth.jwt_service", fromlist=["JWTService"]), "JWTService")
        with pytest.raises((ValueError, TypeError)):
            constructor(secret_key=None)


@final
class TestEncodeToken:
    """Tests for JWTService.encode_token."""

    service = JWTService(secret_key="test-secret-key-for-jwt")

    def test_encode_returns_string(self):
        token = self.service.encode_token(user_id="user1")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_encode_contains_required_claims(self):
        token = self.service.encode_token(user_id="user1")
        payload = jwt.decode(token, "test-secret-key-for-jwt", algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "user1"
        assert payload["role"] == "user"
        assert payload["session_version"] == 0
        assert "iat" in payload
        assert "exp" in payload

    def test_encode_with_custom_role(self):
        token = self.service.encode_token(user_id="admin1", role="admin")
        payload = jwt.decode(token, "test-secret-key-for-jwt", algorithms=[JWT_ALGORITHM])
        assert payload["role"] == "admin"

    def test_encode_with_custom_expiry(self):
        token = self.service.encode_token(user_id="user1", expires_hours=2)
        payload = jwt.decode(token, "test-secret-key-for-jwt", algorithms=[JWT_ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        diff = exp - iat
        assert abs(diff.total_seconds() - 7200) < 5  # 2 hours ± 5s tolerance

    def test_encode_default_expiry(self):
        token = self.service.encode_token(user_id="user1")
        payload = jwt.decode(token, "test-secret-key-for-jwt", algorithms=[JWT_ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        diff = exp - iat
        expected_seconds = DEFAULT_TOKEN_EXPIRY_HOURS * 3600
        assert abs(diff.total_seconds() - expected_seconds) < 5

    def test_different_users_different_tokens(self):
        token1 = self.service.encode_token(user_id="user1")
        token2 = self.service.encode_token(user_id="user2")
        assert token1 != token2


@final
class TestDecodeToken:
    """Tests for JWTService.decode_token."""

    service = JWTService(secret_key="test-secret-key-for-jwt")

    def test_decode_valid_token(self):
        token = self.service.encode_token(user_id="user1", role="admin")
        payload = self.service.decode_token(token)
        assert payload["sub"] == "user1"
        assert payload["role"] == "admin"

    def test_decode_expired_token_raises(self):
        expired_payload = {
            "sub": "user1",
            "role": "user",
            "iat": datetime.now(timezone.utc) - timedelta(hours=10),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(expired_payload, "test-secret-key-for-jwt", algorithm=JWT_ALGORITHM)
        from core.exceptions.auth_exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="expired"):
            self.service.decode_token(token)

    def test_decode_invalid_token_raises(self):
        from core.exceptions.auth_exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="Invalid token"):
            self.service.decode_token("not.a.valid.token")

    def test_decode_wrong_secret_raises(self):
        token = jwt.encode(
            {"sub": "user1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "different-secret",
            algorithm=JWT_ALGORITHM,
        )
        from core.exceptions.auth_exceptions import AuthenticationError

        with pytest.raises(AuthenticationError):
            self.service.decode_token(token)


@final
class TestValidateToken:
    """Tests for JWTService.validate_token."""

    service = JWTService(secret_key="test-secret-key-for-jwt")

    def test_validate_valid_token(self):
        token = self.service.encode_token(user_id="user1")
        payload = self.service.validate_token(token)
        assert payload["sub"] == "user1"

    def test_validate_token_missing_subject(self):
        """Token without 'sub' claim should raise."""
        payload = {
            "role": "user",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, "test-secret-key-for-jwt", algorithm=JWT_ALGORITHM)
        from core.exceptions.auth_exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="subject"):
            self.service.validate_token(token)

    def test_validate_token_missing_session_version(self):
        payload = {
            "sub": "user1",
            "role": "user",
            "jti": "legacy-token",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, "test-secret-key-for-jwt", algorithm=JWT_ALGORITHM)
        from core.exceptions.auth_exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="session version"):
            self.service.validate_token(token)

    def test_validate_expired_token_raises(self):
        expired_payload = {
            "sub": "user1",
            "role": "user",
            "iat": datetime.now(timezone.utc) - timedelta(hours=10),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(expired_payload, "test-secret-key-for-jwt", algorithm=JWT_ALGORITHM)
        from core.exceptions.auth_exceptions import AuthenticationError

        with pytest.raises(AuthenticationError):
            self.service.validate_token(token)


class TestConstants:
    """Tests for module-level constants."""

    def test_jwt_algorithm_is_hs256(self):
        assert JWT_ALGORITHM == "HS256"

    def test_default_expiry_is_int(self):
        assert isinstance(DEFAULT_TOKEN_EXPIRY_HOURS, int)
        assert DEFAULT_TOKEN_EXPIRY_HOURS > 0
