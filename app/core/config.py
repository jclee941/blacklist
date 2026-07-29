"""
Centralized Configuration — Single source of truth for all environment variables.

    from core.config import config
    url = config.COLLECTOR_URL
    db_params = config.get_postgres_params()
"""

import os
from typing import TypedDict

from core.datastore_config import DatastoreConfig


class CollectorAuthRequestKwargs(TypedDict, total=False):
    headers: dict[str, str]
    verify: str


class AppConfig(DatastoreConfig):
    @property
    def COLLECTOR_URL(self) -> str:
        return os.environ.get("COLLECTOR_URL", "https://blacklist-collector:8545")

    @property
    def COLLECTOR_COLLECTION_TIMEOUT(self) -> int:
        return int(os.getenv("COLLECTOR_COLLECTION_TIMEOUT", "360"))

    @property
    def COLLECTOR_AUTH_TOKEN(self) -> str:
        return os.getenv("COLLECTOR_AUTH_TOKEN", "")

    @property
    def COLLECTOR_AUTH_REQUEST_KWARGS(self) -> CollectorAuthRequestKwargs:
        token = self.COLLECTOR_AUTH_TOKEN
        if not token:
            return {"verify": self.INTERNAL_CA_CERT}
        return {
            "headers": {"Authorization": f"Bearer {token}"},
            "verify": self.INTERNAL_CA_CERT,
        }

    @property
    def BLACKLIST_API_URL(self) -> str:
        return os.getenv("BLACKLIST_API_URL", "https://blacklist-app:2542/api")

    @property
    def INTERNAL_TLS_CERT(self) -> str:
        return os.getenv("INTERNAL_TLS_CERT", "/run/blacklist/tls/tls.crt")

    @property
    def INTERNAL_TLS_KEY(self) -> str:
        return os.getenv("INTERNAL_TLS_KEY", "/run/blacklist/tls/tls.key")

    @property
    def REGTECH_BASE_URL(self) -> str:
        return os.getenv("REGTECH_BASE_URL", "https://regtech.fsec.or.kr")

    @property
    def RATE_LIMIT_WHITELIST(self) -> list[str]:
        """Rate limit exempt IPs/prefixes. Entries ending with '.' are prefix matches."""
        return os.getenv("RATE_LIMIT_WHITELIST", "127.0.0.1,localhost,172.,192.168.").split(",")

    @property
    def SECRET_KEY(self) -> str | None:
        return os.getenv("SECRET_KEY")

    @property
    def FLASK_SECRET_KEY(self) -> str | None:
        return os.getenv("FLASK_SECRET_KEY")

    @property
    def JWT_SECRET(self) -> str | None:
        return os.getenv("JWT_SECRET_KEY")

    @property
    def JWT_EXPIRY_HOURS(self) -> int:
        return int(os.getenv("JWT_EXPIRY_HOURS", "8"))

    @property
    def CREDENTIAL_MASTER_KEY(self) -> str | None:
        return os.getenv("CREDENTIAL_MASTER_KEY")

    @property
    def CREDENTIAL_ENCRYPTION_KEY(self) -> str | None:
        return os.getenv("CREDENTIAL_ENCRYPTION_KEY")

    @property
    def ENCRYPTION_SALT(self) -> str | None:
        return os.getenv("ENCRYPTION_SALT")

    @property
    def SETTINGS_ENCRYPTION_KEY(self) -> str | None:
        return os.getenv("SETTINGS_ENCRYPTION_KEY")

    @property
    def ADMIN_USERNAME(self) -> str | None:
        return os.getenv("ADMIN_USERNAME")

    @property
    def ADMIN_PASSWORD(self) -> str | None:
        return os.getenv("ADMIN_PASSWORD")

    @property
    def ADMIN_RESET_KEY(self) -> str | None:
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
    def APP_VERSION(self) -> str | None:
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
