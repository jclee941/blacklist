"""Tests for app/core/config.py — AppConfig class."""

import pytest
from unittest.mock import patch
import os


@pytest.mark.unit
class TestAppConfigDefaults:
    """Verify all properties return correct defaults when env vars are unset."""

    def setup_method(self):
        from app.core.config import AppConfig

        self.config = AppConfig()

    @patch.dict(os.environ, {}, clear=True)
    def test_collector_url_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.COLLECTOR_URL == "http://localhost:8545"

    @patch.dict(os.environ, {}, clear=True)
    def test_collector_api_url_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.COLLECTOR_API_URL == "http://localhost:8545"

    @patch.dict(os.environ, {}, clear=True)
    def test_blacklist_api_url_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.BLACKLIST_API_URL == "http://localhost:2542/api"

    @patch.dict(os.environ, {}, clear=True)
    def test_regtech_base_url_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.REGTECH_BASE_URL == "https://regtech.fsec.or.kr"

    @patch.dict(os.environ, {}, clear=True)
    def test_postgres_defaults(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.POSTGRES_HOST == "blacklist-postgres"
        assert cfg.POSTGRES_PORT == 5432
        assert cfg.POSTGRES_DB == "blacklist"
        assert cfg.POSTGRES_USER == "postgres"
        assert cfg.POSTGRES_PASSWORD == "postgres"

    @patch.dict(os.environ, {}, clear=True)
    def test_redis_defaults(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.REDIS_HOST == "blacklist-redis"
        assert cfg.REDIS_PORT == 6379

    @patch.dict(os.environ, {}, clear=True)
    def test_jwt_expiry_hours_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.JWT_EXPIRY_HOURS == 8

    @patch.dict(os.environ, {}, clear=True)
    def test_admin_defaults(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.ADMIN_USERNAME == "admin"
        assert cfg.ADMIN_PASSWORD == "admin"

    @patch.dict(os.environ, {}, clear=True)
    def test_app_port_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.APP_PORT == 2542

    @patch.dict(os.environ, {}, clear=True)
    def test_flask_env_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.FLASK_ENV == "production"

    @patch.dict(os.environ, {}, clear=True)
    def test_log_level_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.LOG_LEVEL == "INFO"

    @patch.dict(os.environ, {}, clear=True)
    def test_collection_interval_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.COLLECTION_INTERVAL == 3600

    @patch.dict(os.environ, {}, clear=True)
    def test_db_connect_retries_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.DB_CONNECT_RETRIES == 10

    @patch.dict(os.environ, {}, clear=True)
    def test_db_backoff_delay_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.DB_BACKOFF_DELAY == 2.0

    @patch.dict(os.environ, {}, clear=True)
    def test_version_defaults(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.VERSION == "unknown"
        assert cfg.VCS_REF == "unknown"

    @patch.dict(os.environ, {}, clear=True)
    def test_service_name_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.SERVICE_NAME == "blacklist-app"
        assert cfg.ENVIRONMENT == "production"

    @patch.dict(os.environ, {}, clear=True)
    def test_log_dir_default(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.LOG_DIR == "/app/logs"


@pytest.mark.unit
class TestAppConfigEnvOverrides:
    """Verify env vars properly override defaults."""

    def test_collector_url_override(self):
        with patch.dict(os.environ, {"COLLECTOR_URL": "http://collector:9999"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.COLLECTOR_URL == "http://collector:9999"

    def test_postgres_host_override(self):
        with patch.dict(os.environ, {"POSTGRES_HOST": "db.example.com"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.POSTGRES_HOST == "db.example.com"

    def test_postgres_port_override(self):
        with patch.dict(os.environ, {"POSTGRES_PORT": "5433"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.POSTGRES_PORT == 5433

    def test_redis_port_override(self):
        with patch.dict(os.environ, {"REDIS_PORT": "6380"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.REDIS_PORT == 6380

    def test_app_port_override(self):
        with patch.dict(os.environ, {"APP_PORT": "8080"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.APP_PORT == 8080

    def test_jwt_expiry_hours_override(self):
        with patch.dict(os.environ, {"JWT_EXPIRY_HOURS": "24"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.JWT_EXPIRY_HOURS == 24

    def test_collection_interval_override(self):
        with patch.dict(os.environ, {"COLLECTION_INTERVAL": "7200"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.COLLECTION_INTERVAL == 7200

    def test_db_backoff_delay_override(self):
        with patch.dict(os.environ, {"DB_BACKOFF_DELAY": "5.5"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.DB_BACKOFF_DELAY == 5.5

    def test_secret_key_override(self):
        with patch.dict(os.environ, {"SECRET_KEY": "my-secret"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.SECRET_KEY == "my-secret"

    def test_fmg_host_override(self):
        with patch.dict(os.environ, {"FMG_HOST": "10.0.0.1"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.FMG_HOST == "10.0.0.1"

    def test_migration_key_override(self):
        with patch.dict(os.environ, {"MIGRATION_KEY": "new-key-2026"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.MIGRATION_KEY == "new-key-2026"


@pytest.mark.unit
class TestAppConfigBooleans:
    """Verify boolean properties handle truthy/falsy strings."""

    @pytest.mark.parametrize("value", ["true", "1", "yes"])
    def test_disable_jwt_auth_truthy(self, value):
        with patch.dict(os.environ, {"DISABLE_JWT_AUTH": value}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.DISABLE_JWT_AUTH is True

    @pytest.mark.parametrize("value", ["false", "0", "no", ""])
    def test_disable_jwt_auth_falsy(self, value):
        with patch.dict(os.environ, {"DISABLE_JWT_AUTH": value}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.DISABLE_JWT_AUTH is False

    def test_debug_true(self):
        with patch.dict(os.environ, {"FLASK_DEBUG": "true"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.DEBUG is True

    def test_debug_false(self):
        with patch.dict(os.environ, {"FLASK_DEBUG": "false"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.DEBUG is False

    def test_testing_true(self):
        with patch.dict(os.environ, {"TESTING": "True"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.TESTING is True

    def test_testing_false(self):
        with patch.dict(os.environ, {"TESTING": "false"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.TESTING is False

    def test_use_real_db_true(self):
        with patch.dict(os.environ, {"USE_REAL_DB": "True"}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.USE_REAL_DB is True

    @pytest.mark.parametrize("value", ["true", "1", "yes"])
    def test_disable_auto_collection_truthy(self, value):
        with patch.dict(os.environ, {"DISABLE_AUTO_COLLECTION": value}):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.DISABLE_AUTO_COLLECTION is True


@pytest.mark.unit
class TestAppConfigPostgres:
    """Verify Postgres connection methods."""

    def test_get_postgres_params_from_individual_vars(self):
        env = {
            "POSTGRES_HOST": "db-host",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "mydb",
            "POSTGRES_USER": "myuser",
            "POSTGRES_PASSWORD": "mypass",
        }
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            params = cfg.get_postgres_params()
            assert params["host"] == "db-host"
            assert params["port"] == 5433
            assert params["database"] == "mydb"
            assert params["user"] == "myuser"
            assert params["password"] == "mypass"

    def test_get_postgres_params_from_database_url(self):
        env = {"DATABASE_URL": "postgresql://urluser:urlpass@urlhost:5434/urldb"}
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            params = cfg.get_postgres_params()
            assert params["host"] == "urlhost"
            assert params["port"] == 5434
            assert params["database"] == "urldb"
            assert params["user"] == "urluser"
            assert params["password"] == "urlpass"

    def test_get_postgres_params_database_url_overrides_individual(self):
        env = {
            "DATABASE_URL": "postgresql://urluser:urlpass@urlhost:5434/urldb",
            "POSTGRES_HOST": "should-be-ignored",
        }
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            params = cfg.get_postgres_params()
            assert params["host"] == "urlhost"

    def test_get_postgres_params_postgres_url_fallback(self):
        env = {"POSTGRES_URL": "postgresql://pu:pp@ph:5435/pd"}
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            params = cfg.get_postgres_params()
            assert params["host"] == "ph"
            assert params["port"] == 5435

    def test_postgres_url_prefers_database_url(self):
        env = {
            "DATABASE_URL": "postgresql://a:b@c:1/d",
            "POSTGRES_URL": "postgresql://x:y@z:2/w",
        }
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.POSTGRES_URL == "postgresql://a:b@c:1/d"

    def test_postgres_url_none_when_unset(self):
        with patch.dict(os.environ, {}, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.POSTGRES_URL is None

    def test_get_postgres_dsn_from_url(self):
        env = {"DATABASE_URL": "postgresql://u:p@h:5432/db"}
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.get_postgres_dsn() == "postgresql://u:p@h:5432/db"

    def test_get_postgres_dsn_constructed(self):
        env = {
            "POSTGRES_USER": "myuser",
            "POSTGRES_PASSWORD": "mypass",
            "POSTGRES_HOST": "myhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "mydb",
        }
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            dsn = cfg.get_postgres_dsn()
            assert dsn == "postgresql://myuser:mypass@myhost:5432/mydb"

    def test_get_postgres_params_url_missing_parts_use_defaults(self):
        env = {"DATABASE_URL": "postgresql:///mydb"}
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            params = cfg.get_postgres_params()
            assert params["host"] == "localhost"
            assert params["port"] == 5432
            assert params["database"] == "mydb"
            assert params["user"] == "postgres"


@pytest.mark.unit
class TestAppConfigRedis:
    """Verify Redis connection methods."""

    def test_redis_url_computed(self):
        env = {"REDIS_HOST": "redis-host", "REDIS_PORT": "6380"}
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.REDIS_URL == "redis://redis-host:6380"

    def test_get_redis_params(self):
        env = {"REDIS_HOST": "redis-host", "REDIS_PORT": "6380"}
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            params = cfg.get_redis_params()
            assert params["host"] == "redis-host"
            assert params["port"] == 6380


@pytest.mark.unit
class TestAppConfigOptionalProperties:
    """Verify optional properties return None when unset."""

    @patch.dict(os.environ, {}, clear=True)
    def test_optional_properties_none_when_unset(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.SECRET_KEY is None
        assert cfg.FLASK_SECRET_KEY is None
        assert cfg.JWT_SECRET is None
        assert cfg.CREDENTIAL_MASTER_KEY is None
        assert cfg.CREDENTIAL_ENCRYPTION_KEY is None
        assert cfg.ENCRYPTION_SALT is None
        assert cfg.SETTINGS_ENCRYPTION_KEY is None
        assert cfg.FMG_HOST is None
        assert cfg.FMG_PASS is None
        assert cfg.ADMIN_RESET_KEY is None
        assert cfg.APP_VERSION is None

    @patch.dict(os.environ, {}, clear=True)
    def test_empty_string_defaults(self):
        from app.core.config import AppConfig

        cfg = AppConfig()
        assert cfg.REGTECH_ID == ""
        assert cfg.REGTECH_PW == ""
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
        from app.core.config import config, AppConfig

        assert isinstance(config, AppConfig)
