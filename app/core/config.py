"""
Centralized Configuration — Single source of truth for all environment variables.

    from core.config import config
    url = config.COLLECTOR_URL
    db_params = config.get_postgres_params()
"""

import os
from typing import Any, Optional, TypedDict
from urllib.parse import quote, urlparse


class RedisAuthParams(TypedDict, total=False):
    """Redis auth kwargs. Absent when no password is set — password="" is not the same as omitting it."""

    password: str


class CollectorAuthRequestKwargs(TypedDict, total=False):
    headers: dict[str, str]


class AppConfig:
    @property
    def COLLECTOR_URL(self) -> str:
        return os.environ.get("COLLECTOR_URL", "http://blacklist-collector:8545")

    @property
    def COLLECTOR_AUTH_TOKEN(self) -> str:
        return os.getenv("COLLECTOR_AUTH_TOKEN", "")

    @property
    def COLLECTOR_AUTH_REQUEST_KWARGS(self) -> CollectorAuthRequestKwargs:
        token = self.COLLECTOR_AUTH_TOKEN
        if not token:
            return {}
        return {"headers": {"Authorization": f"Bearer {token}"}}

    @property
    def BLACKLIST_API_URL(self) -> str:
        return os.getenv("BLACKLIST_API_URL", "http://blacklist-app:2542/api")

    @property
    def REGTECH_BASE_URL(self) -> str:
        return os.getenv("REGTECH_BASE_URL", "https://regtech.fsec.or.kr")

    @property
    def POSTGRES_HOST(self) -> str:
        return os.getenv("POSTGRES_HOST", "blacklist-postgres")

    @property
    def POSTGRES_PORT(self) -> int:
        return int(os.getenv("POSTGRES_PORT", "5432"))

    @property
    def POSTGRES_DB(self) -> str:
        return os.getenv("POSTGRES_DB", "blacklist")

    @property
    def POSTGRES_USER(self) -> str:
        return os.getenv("POSTGRES_USER", "postgres")

    @property
    def POSTGRES_PASSWORD(self) -> str:
        return os.getenv("POSTGRES_PASSWORD", "postgres")

    @property
    def POSTGRES_FALLBACK_HOSTS(self) -> list[str]:
        """Comma-separated fallback hosts for DB connection retry."""
        raw = os.getenv("POSTGRES_FALLBACK_HOSTS", "blacklist-postgres,postgres,localhost")
        return [h.strip() for h in raw.split(",") if h.strip()]

    @property
    def POSTGRES_URL(self) -> Optional[str]:
        return os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

    def get_postgres_params(self) -> dict[str, Any]:
        """Return connection params, preferring DATABASE_URL/POSTGRES_URL if set."""
        url = self.POSTGRES_URL
        if url:
            parsed = urlparse(url)
            return {
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 5432,
                "database": parsed.path.lstrip("/") or "blacklist",
                "user": parsed.username or "postgres",
                "password": parsed.password or self.POSTGRES_PASSWORD,
            }
        return {
            "host": self.POSTGRES_HOST,
            "port": self.POSTGRES_PORT,
            "database": self.POSTGRES_DB,
            "user": self.POSTGRES_USER,
            "password": self.POSTGRES_PASSWORD,
        }

    def get_postgres_dsn(self) -> str:
        if self.POSTGRES_URL:
            return self.POSTGRES_URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_HOST(self) -> str:
        return os.getenv("REDIS_HOST", "blacklist-redis")

    @property
    def REDIS_PORT(self) -> int:
        return int(os.getenv("REDIS_PORT", "6379"))

    @property
    def REDIS_PASSWORD(self) -> str:
        return os.getenv("REDIS_PASSWORD", "")

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{quote(self.REDIS_PASSWORD, safe='')}@{self.REDIS_HOST}:{self.REDIS_PORT}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    def get_redis_auth_params(self) -> RedisAuthParams:
        if not self.REDIS_PASSWORD:
            return {}
        return {"password": self.REDIS_PASSWORD}

    def get_redis_params(self) -> dict[str, int | str]:
        params: dict[str, int | str] = {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
        }
        if self.REDIS_PASSWORD:
            params["password"] = self.REDIS_PASSWORD
        return params

    @property
    def RATE_LIMIT_WHITELIST(self) -> list[str]:
        """Rate limit exempt IPs/prefixes. Entries ending with '.' are prefix matches."""
        return os.getenv("RATE_LIMIT_WHITELIST", "127.0.0.1,localhost,172.,192.168.").split(",")

    @property
    def SECRET_KEY(self) -> Optional[str]:
        return os.getenv("SECRET_KEY")

    @property
    def FLASK_SECRET_KEY(self) -> Optional[str]:
        return os.getenv("FLASK_SECRET_KEY")

    @property
    def JWT_SECRET(self) -> Optional[str]:
        return os.getenv("JWT_SECRET_KEY")

    @property
    def JWT_EXPIRY_HOURS(self) -> int:
        return int(os.getenv("JWT_EXPIRY_HOURS", "8"))

    @property
    def CREDENTIAL_MASTER_KEY(self) -> Optional[str]:
        return os.getenv("CREDENTIAL_MASTER_KEY")

    @property
    def CREDENTIAL_ENCRYPTION_KEY(self) -> Optional[str]:
        return os.getenv("CREDENTIAL_ENCRYPTION_KEY")

    @property
    def ENCRYPTION_SALT(self) -> Optional[str]:
        return os.getenv("ENCRYPTION_SALT")

    @property
    def SETTINGS_ENCRYPTION_KEY(self) -> Optional[str]:
        return os.getenv("SETTINGS_ENCRYPTION_KEY")

    @property
    def ADMIN_USERNAME(self) -> str | None:
        return os.getenv("ADMIN_USERNAME")

    @property
    def ADMIN_PASSWORD(self) -> str | None:
        return os.getenv("ADMIN_PASSWORD")

    @property
    def ADMIN_RESET_KEY(self) -> Optional[str]:
        return os.getenv("ADMIN_RESET_KEY")

    @property
    def MIGRATION_KEY(self) -> str:
        return os.getenv("MIGRATION_KEY", "cleanup-2025-09-03")

    @property
    def DISABLE_JWT_AUTH(self) -> bool:
        return os.getenv("DISABLE_JWT_AUTH", "").lower() in ("true", "1", "yes")

    @property
    def GITHUB_TOKEN(self) -> str:
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def GITHUB_REPO_OWNER(self) -> str:
        return os.getenv("GITHUB_REPO_OWNER", "")

    @property
    def GITHUB_REPO_NAME(self) -> str:
        return os.getenv("GITHUB_REPO_NAME", "")

    @property
    def APP_PORT(self) -> int:
        return int(os.getenv("APP_PORT", "2542"))

    @property
    def FRONTEND_PORT(self) -> int:
        return int(os.getenv("FRONTEND_PORT", "2543"))

    @property
    def COLLECTOR_PORT(self) -> int:
        return int(os.getenv("COLLECTOR_PORT", "8545"))

    @property
    def APP_VERSION(self) -> Optional[str]:
        return os.getenv("APP_VERSION")

    @property
    def COMMIT_HASH(self) -> str:
        return os.getenv("COMMIT_HASH", "").strip()

    @property
    def BUILD_NUMBER(self) -> str:
        return os.getenv("BUILD_NUMBER", "").strip()

    @property
    def VERSION(self) -> str:
        return os.getenv("VERSION", "unknown")

    @property
    def VCS_REF(self) -> str:
        return os.getenv("VCS_REF", "unknown")

    @property
    def DEBUG(self) -> bool:
        return os.getenv("FLASK_DEBUG", "false").lower() == "true"

    @property
    def FLASK_ENV(self) -> str:
        return os.getenv("FLASK_ENV", "production")

    @property
    def LOG_LEVEL(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")

    @property
    def TESTING(self) -> bool:
        return os.getenv("TESTING") == "True"

    @property
    def USE_REAL_DB(self) -> bool:
        return os.getenv("USE_REAL_DB") == "True"

    @property
    def COLLECTION_INTERVAL(self) -> int:
        return int(os.getenv("COLLECTION_INTERVAL", "3600"))

    @property
    def DB_CONNECT_RETRIES(self) -> int:
        return int(os.getenv("DB_CONNECT_RETRIES", "10"))

    @property
    def DB_BACKOFF_DELAY(self) -> float:
        return float(os.getenv("DB_BACKOFF_DELAY", "2.0"))

    @property
    def DISABLE_AUTO_COLLECTION(self) -> bool:
        return os.getenv("DISABLE_AUTO_COLLECTION", "").lower() in ("true", "1", "yes")

    @property
    def ENVIRONMENT(self) -> str:
        return os.getenv("ENVIRONMENT", "production")

    @property
    def SERVICE_NAME(self) -> str:
        return os.getenv("SERVICE_NAME", "blacklist-app")

    @property
    def HOSTNAME(self) -> str:
        return os.getenv("HOSTNAME", "unknown")

    @property
    def LOG_DIR(self) -> str:
        return os.getenv("LOG_DIR", "/app/logs")


config = AppConfig()
