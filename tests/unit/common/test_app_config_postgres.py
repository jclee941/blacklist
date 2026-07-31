import os
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestAppConfigPostgres:
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

    def test_get_postgres_params_requires_verified_tls(self):
        env = {"INTERNAL_CA_CERT": "/probe/ca.crt"}
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            params = AppConfig().get_postgres_params()

        assert params["sslmode"] == "verify-full"
        assert params["sslrootcert"] == "/probe/ca.crt"

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
            assert cfg.get_postgres_dsn() == (
                "postgresql://u:p@h:5432/db?sslmode=verify-full&sslrootcert=%2Frun%2Fblacklist%2Fca.crt"
            )

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
            assert dsn == (
                "postgresql://myuser:mypass@myhost:5432/mydb"
                "?sslmode=verify-full&sslrootcert=%2Frun%2Fblacklist%2Fca.crt"
            )

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
