"""Authentication state, password hashing, lockout, and JWT revocation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final, Protocol

import bcrypt


LOGIN_FAILURE_LIMIT: Final = 5
LOGIN_LOCK_SECONDS: Final = 15 * 60
MIN_PASSWORD_LENGTH: Final = 12
MAX_PASSWORD_BYTES: Final = 72


@dataclass(frozen=True, slots=True)
class AuthSecurityBackendError(Exception):
    received_type: str

    def __str__(self) -> str:
        return f"Unexpected authentication store value type: {self.received_type}"


@dataclass(frozen=True, slots=True)
class PasswordPolicyError(Exception):
    def __str__(self) -> str:
        return "Password must be at least 12 characters and at most 72 UTF-8 bytes"


class SecurityStore(Protocol):
    def get(self, key: str) -> str | bytes | None: ...

    def incr(self, key: str) -> int: ...

    def expire(self, key: str, seconds: int) -> bool: ...

    def delete(self, *keys: str) -> int: ...

    def setex(self, key: str, seconds: int, value: str) -> bool: ...


class RevocationChecker(Protocol):
    def is_revoked(self, jti: str) -> bool: ...

    def revoke(self, jti: str, expires_at: int) -> None: ...

    def current_session_version(self, subject: str) -> int: ...

    def invalidate_sessions(self, subject: str) -> int: ...


class RedisSecurityStore:
    def __init__(self, client) -> None:
        self._client = client

    def get(self, key: str) -> str | bytes | None:
        value = self._client.get(key)
        if value is None or isinstance(value, (str, bytes)):
            return value
        raise AuthSecurityBackendError(type(value).__name__)

    def incr(self, key: str) -> int:
        value = self._client.incr(key)
        if isinstance(value, int):
            return value
        raise AuthSecurityBackendError(type(value).__name__)

    def expire(self, key: str, seconds: int) -> bool:
        return bool(self._client.expire(key, seconds))

    def delete(self, *keys: str) -> int:
        value = self._client.delete(*keys)
        if isinstance(value, int):
            return value
        raise AuthSecurityBackendError(type(value).__name__)

    def setex(self, key: str, seconds: int, value: str) -> bool:
        return bool(self._client.setex(key, seconds, value))


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password) < MIN_PASSWORD_LENGTH or len(password_bytes) > MAX_PASSWORD_BYTES:
        raise PasswordPolicyError
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(candidate: str, configured: str) -> tuple[bool, str | None]:
    """Hash-verify a configured password and return an upgrade hash for legacy plaintext."""
    candidate_bytes = candidate.encode("utf-8")
    if len(candidate_bytes) > MAX_PASSWORD_BYTES:
        return False, None
    configured_bytes = configured.encode("utf-8")
    if configured.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(candidate_bytes, configured_bytes), None
        except ValueError:
            return False, None

    upgraded = bcrypt.hashpw(configured_bytes[:MAX_PASSWORD_BYTES], bcrypt.gensalt())
    return bcrypt.checkpw(candidate_bytes, upgraded), upgraded.decode("utf-8")


class AuthSecurity:
    def __init__(self, store: SecurityStore) -> None:
        self._store = store

    @staticmethod
    def _login_key(username: str, client_ip: str) -> str:
        identity = hashlib.sha256(f"{username.casefold()}\0{client_ip}".encode()).hexdigest()
        return f"auth:login-failures:{identity}"

    def is_login_locked(self, username: str, client_ip: str) -> bool:
        value = self._store.get(self._login_key(username, client_ip))
        if value is None:
            return False
        if isinstance(value, bytes):
            value = value.decode("ascii")
        return int(value) >= LOGIN_FAILURE_LIMIT

    def record_login_failure(self, username: str, client_ip: str) -> None:
        key = self._login_key(username, client_ip)
        failures = self._store.incr(key)
        if failures == 1:
            self._store.expire(key, LOGIN_LOCK_SECONDS)

    def clear_login_failures(self, username: str, client_ip: str) -> None:
        self._store.delete(self._login_key(username, client_ip))

    def is_revoked(self, jti: str) -> bool:
        return self._store.get(f"auth:revoked:{jti}") is not None

    def revoke(self, jti: str, expires_at: int) -> None:
        now = int(datetime.now(timezone.utc).timestamp())
        ttl = max(1, expires_at - now)
        self._store.setex(f"auth:revoked:{jti}", ttl, "1")

    @staticmethod
    def _session_version_key(subject: str) -> str:
        identity = hashlib.sha256(subject.casefold().encode()).hexdigest()
        return f"auth:session-version:{identity}"

    def current_session_version(self, subject: str) -> int:
        value = self._store.get(self._session_version_key(subject))
        if value is None:
            return 0
        if isinstance(value, bytes):
            value = value.decode("ascii")
        try:
            version = int(value)
        except ValueError:
            raise AuthSecurityBackendError(type(value).__name__) from None
        if version < 0:
            raise AuthSecurityBackendError(type(value).__name__)
        return version

    def invalidate_sessions(self, subject: str) -> int:
        return self._store.incr(self._session_version_key(subject))
