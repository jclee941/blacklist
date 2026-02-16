"""
JWT Service — token encoding, decoding, and validation.

Registered as app.extensions['jwt_service'].
Security-critical: handles all token lifecycle operations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from core.config import config
from core.exceptions.auth_exceptions import AuthenticationError

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_EXPIRY_HOURS = config.JWT_EXPIRY_HOURS
JWT_ALGORITHM = "HS256"


class JWTService:
    def __init__(self, secret_key: str) -> None:
        if not secret_key:
            raise ValueError("JWT secret_key must not be empty")
        self._secret_key = secret_key

    def encode_token(
        self,
        user_id: str,
        role: str = "user",
        expires_hours: int | None = None,
    ) -> str:
        exp_hours = expires_hours or DEFAULT_TOKEN_EXPIRY_HOURS
        now = datetime.now(timezone.utc)
        payload: dict[str, Any] = {
            "sub": user_id,
            "role": role,
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
        return payload
