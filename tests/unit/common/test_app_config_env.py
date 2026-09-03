import os
from unittest.mock import patch

import pytest

from app.core.config import AppConfig


@pytest.mark.unit
class TestAppConfigEnvOverrides:
    def test_collector_url_override(self):
        with patch.dict(os.environ, {"COLLECTOR_URL": "http://collector:9999"}):
            cfg = AppConfig()
            assert cfg.COLLECTOR_URL == "http://collector:9999"

    def test_collector_collection_timeout_override(self):
        with patch.dict(os.environ, {"COLLECTOR_COLLECTION_TIMEOUT": "480"}):
            cfg = AppConfig()

            assert cfg.COLLECTOR_COLLECTION_TIMEOUT == 480

    def test_postgres_host_override(self):
        with patch.dict(os.environ, {"POSTGRES_HOST": "db.example.com"}):
            cfg = AppConfig()
            assert cfg.POSTGRES_HOST == "db.example.com"

    def test_postgres_port_override(self):
        with patch.dict(os.environ, {"POSTGRES_PORT": "5433"}):
            cfg = AppConfig()
            assert cfg.POSTGRES_PORT == 5433

    def test_redis_port_override(self):
        with patch.dict(os.environ, {"REDIS_PORT": "6380"}):
            cfg = AppConfig()
            assert cfg.REDIS_PORT == 6380

    def test_app_port_override(self):
        with patch.dict(os.environ, {"APP_PORT": "8080"}):
            cfg = AppConfig()
            assert cfg.APP_PORT == 8080

    def test_jwt_expiry_hours_override(self):
        with patch.dict(os.environ, {"JWT_EXPIRY_HOURS": "24"}):
            cfg = AppConfig()
            assert cfg.JWT_EXPIRY_HOURS == 24

    def test_collection_interval_override(self):
        with patch.dict(os.environ, {"COLLECTION_INTERVAL": "7200"}):
            cfg = AppConfig()
            assert cfg.COLLECTION_INTERVAL == 7200

    def test_db_backoff_delay_override(self):
        with patch.dict(os.environ, {"DB_BACKOFF_DELAY": "5.5"}):
            cfg = AppConfig()
            assert cfg.DB_BACKOFF_DELAY == 5.5

    def test_secret_key_override(self):
        with patch.dict(os.environ, {"SECRET_KEY": "my-secret"}):
            cfg = AppConfig()
            assert cfg.SECRET_KEY == "my-secret"

    def test_obsolete_migration_key_is_not_configuration(self):
        cfg = AppConfig()

        assert not hasattr(cfg, "MIGRATION_KEY")


@pytest.mark.unit
class TestAppConfigBooleans:
    @pytest.mark.parametrize("value", ["true", "1", "yes"])
    def test_disable_jwt_auth_truthy(self, value):
        with patch.dict(os.environ, {"DISABLE_JWT_AUTH": value}):
            cfg = AppConfig()
            assert cfg.DISABLE_JWT_AUTH is True

    @pytest.mark.parametrize("value", ["false", "0", "no", ""])
    def test_disable_jwt_auth_falsy(self, value):
        with patch.dict(os.environ, {"DISABLE_JWT_AUTH": value}):
            cfg = AppConfig()
            assert cfg.DISABLE_JWT_AUTH is False

    def test_debug_true(self):
        with patch.dict(os.environ, {"FLASK_DEBUG": "true"}):
            cfg = AppConfig()
            assert cfg.DEBUG is True

    def test_debug_false(self):
        with patch.dict(os.environ, {"FLASK_DEBUG": "false"}):
            cfg = AppConfig()
            assert cfg.DEBUG is False

    def test_testing_true(self):
        with patch.dict(os.environ, {"TESTING": "True"}):
            cfg = AppConfig()
            assert cfg.TESTING is True

    def test_testing_false(self):
        with patch.dict(os.environ, {"TESTING": "false"}):
            cfg = AppConfig()
            assert cfg.TESTING is False

    def test_use_real_db_true(self):
        with patch.dict(os.environ, {"USE_REAL_DB": "True"}):
            cfg = AppConfig()
            assert cfg.USE_REAL_DB is True

    @pytest.mark.parametrize("value", ["true", "1", "yes"])
    def test_disable_auto_collection_truthy(self, value):
        with patch.dict(os.environ, {"DISABLE_AUTO_COLLECTION": value}):
            cfg = AppConfig()
            assert cfg.DISABLE_AUTO_COLLECTION is True
