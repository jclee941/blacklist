"""
JWT Service — token encoding, decoding, and validation.

Registered as app.extensions['jwt_service'].
Security-critical: handles all token lifecycle operations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import uuid4

import jwt

from core.config import config
from core.exceptions.auth_exceptions import AuthenticationError
from core.auth.security import RevocationChecker

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_EXPIRY_HOURS = config.JWT_EXPIRY_HOURS
JWT_ALGORITHM = "HS256"


class SessionVersionChecker(Protocol):
    def current_session_version(self, subject: str) -> int: ...


class JWTService:
    def __init__(
        self,
        secret_key: str,
        revocations: RevocationChecker | None = None,
        session_versions: SessionVersionChecker | None = None,
        expiry_hours: int = DEFAULT_TOKEN_EXPIRY_HOURS,
    ) -> None:
        if not secret_key:
            raise ValueError("JWT secret_key must not be empty")
        if expiry_hours < 1:
            raise ValueError("JWT expiry_hours must be positive")
        self._secret_key = secret_key
        self._revocations = revocations
        self._session_versions = session_versions
        self._expiry_hours = expiry_hours

    @property
    def expiry_seconds(self) -> int:
        return self._expiry_hours * 60 * 60

    def encode_token(
        self,
        user_id: str,
        role: str = "user",
        expires_hours: int | None = None,
        session_version: int | None = None,
    ) -> str:
        exp_hours = self._expiry_hours if expires_hours is None else expires_hours
        now = datetime.now(timezone.utc)
        effective_session_version = (
            session_version
            if session_version is not None
            else self._session_versions.current_session_version(user_id)
            if self._session_versions
            else 0
        )
        payload: dict[str, Any] = {
            "sub": user_id,
            "role": role,
            "jti": str(uuid4()),
            "session_version": effective_session_version,
            "iat": now,
            "exp": now + timedelta(hours=exp_hours),
        }
        return jwt.encode(payload, self._secret_key, algorithm=JWT_ALGORITHM)

    def decode_token(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, self._secret_key, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")

    def validate_token(self, token: str) -> dict[str, Any]:
        payload = self.decode_token(token)
        if "sub" not in payload:
            raise AuthenticationError("Token missing subject claim")
        subject = payload["sub"]
        if not isinstance(subject, str) or not subject:
            raise AuthenticationError("Token has invalid subject claim")
        jti = payload.get("jti")
        if not isinstance(jti, str) or not jti:
            raise AuthenticationError("Token missing identifier claim")
        session_version = payload.get("session_version")
        if not isinstance(session_version, int) or isinstance(session_version, bool) or session_version < 0:
            raise AuthenticationError("Token missing session version claim")
        if self._revocations is not None and self._revocations.is_revoked(jti):
            raise AuthenticationError("Token has been revoked")
        if (
            self._session_versions is not None
            and self._session_versions.current_session_version(subject) != session_version
        ):
            raise AuthenticationError("Token session has been invalidated")
        return payload

    def revoke_token(self, token: str) -> None:
        if self._revocations is None:
            raise AuthenticationError("Token revocation service unavailable")
        payload = self.decode_token(token)
        jti = payload.get("jti")
        expires_at = payload.get("exp")
        if not isinstance(jti, str) or not isinstance(expires_at, int):
            raise AuthenticationError("Token missing revocation claims")
        self._revocations.revoke(jti, expires_at)
