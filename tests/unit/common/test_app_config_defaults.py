import os
from unittest.mock import patch

import pytest

from app.core.config import AppConfig


@pytest.mark.unit
class TestAppConfigDefaults:
    """Verify all properties return correct defaults when env vars are unset."""

    @patch.dict(os.environ, {}, clear=True)
    def test_collector_url_default(self):
        cfg = AppConfig()
        assert cfg.COLLECTOR_URL == "https://blacklist-collector:8545"

    @patch.dict(os.environ, {}, clear=True)
    def test_collector_collection_timeout_default(self):
        cfg = AppConfig()

        assert cfg.COLLECTOR_COLLECTION_TIMEOUT == 360

    @patch.dict(os.environ, {}, clear=True)
    def test_blacklist_api_url_default(self):
        cfg = AppConfig()
        assert cfg.BLACKLIST_API_URL == "https://blacklist-app:2542/api"

    @patch.dict(os.environ, {}, clear=True)
    def test_regtech_base_url_default(self):
        cfg = AppConfig()
        assert cfg.REGTECH_BASE_URL == "https://regtech.fsec.or.kr"

    @patch.dict(os.environ, {}, clear=True)
    def test_postgres_defaults(self):
        cfg = AppConfig()
        assert cfg.POSTGRES_HOST == "blacklist-postgres"
        assert cfg.POSTGRES_PORT == 5432
        assert cfg.POSTGRES_DB == "blacklist"
        assert cfg.POSTGRES_USER == "postgres"
        assert cfg.POSTGRES_PASSWORD == "postgres"

    @patch.dict(os.environ, {}, clear=True)
    def test_redis_defaults(self):
        cfg = AppConfig()
        assert cfg.REDIS_HOST == "blacklist-redis"
        assert cfg.REDIS_PORT == 6379

    @patch.dict(os.environ, {}, clear=True)
    def test_jwt_expiry_hours_default(self):
        cfg = AppConfig()
        assert cfg.JWT_EXPIRY_HOURS == 8

    @patch.dict(os.environ, {}, clear=True)
    def test_admin_defaults(self):
        cfg = AppConfig()
        assert cfg.ADMIN_USERNAME is None
        assert cfg.ADMIN_PASSWORD is None

    @patch.dict(os.environ, {}, clear=True)
    def test_app_port_default(self):
        cfg = AppConfig()
        assert cfg.APP_PORT == 2542

    @patch.dict(os.environ, {}, clear=True)
    def test_flask_env_default(self):
        cfg = AppConfig()
        assert cfg.FLASK_ENV == "production"

    @patch.dict(os.environ, {}, clear=True)
    def test_log_level_default(self):
        cfg = AppConfig()
        assert cfg.LOG_LEVEL == "INFO"

    @patch.dict(os.environ, {}, clear=True)
    def test_collection_interval_default(self):
        cfg = AppConfig()
        assert cfg.COLLECTION_INTERVAL == 3600

    @patch.dict(os.environ, {}, clear=True)
    def test_db_connect_retries_default(self):
        cfg = AppConfig()
        assert cfg.DB_CONNECT_RETRIES == 10

    @patch.dict(os.environ, {}, clear=True)
    def test_db_backoff_delay_default(self):
        cfg = AppConfig()
        assert cfg.DB_BACKOFF_DELAY == 2.0

    @patch.dict(os.environ, {}, clear=True)
    def test_version_defaults(self):
        cfg = AppConfig()
        assert cfg.VERSION == "unknown"
        assert cfg.VCS_REF == "unknown"

    @patch.dict(os.environ, {"APP_VERSION": "5.1.2"}, clear=True)
    def test_runtime_version_uses_app_version(self):
        cfg = AppConfig()
        assert cfg.VERSION == "5.1.2"

    @patch.dict(os.environ, {}, clear=True)
    def test_service_name_default(self):
        cfg = AppConfig()
        assert cfg.SERVICE_NAME == "blacklist-app"
        assert cfg.ENVIRONMENT == "production"

    @patch.dict(os.environ, {}, clear=True)
    def test_log_dir_default(self):
        cfg = AppConfig()
        assert cfg.LOG_DIR == "/app/logs"


@pytest.mark.unit
class TestAppConfigOptionalProperties:
    """Verify optional properties return None when unset."""

    @patch.dict(os.environ, {}, clear=True)
    def test_optional_properties_none_when_unset(self):
        cfg = AppConfig()
        assert cfg.SECRET_KEY is None
        assert cfg.FLASK_SECRET_KEY is None
        assert cfg.JWT_SECRET is None
        assert cfg.CREDENTIAL_MASTER_KEY is None
        assert cfg.CREDENTIAL_ENCRYPTION_KEY is None
        assert cfg.ENCRYPTION_SALT is None
        assert cfg.SETTINGS_ENCRYPTION_KEY is None
        assert cfg.ADMIN_RESET_KEY is None
        assert cfg.APP_VERSION is None

    @patch.dict(os.environ, {}, clear=True)
    def test_empty_string_defaults(self):
        cfg = AppConfig()
        assert cfg.GITHUB_TOKEN == ""
        assert cfg.GITHUB_REPO_OWNER == ""
        assert cfg.GITHUB_REPO_NAME == ""


@pytest.mark.unit
class TestAppConfigModuleSingleton:
    """Verify the module-level config singleton."""

    def test_module_singleton_exists(self):
        from app.core.config import config

        assert config is not None
        assert isinstance(config, object)

    def test_module_singleton_is_appconfig(self):
        from app.core.config import config

        assert isinstance(config, AppConfig)
