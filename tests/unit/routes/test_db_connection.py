"""Tests for core/database/connection.py — _get_connection_params."""

from unittest.mock import patch

from core.database.connection import _get_connection_params


class TestGetConnectionParams:
    @patch.dict("os.environ", {}, clear=True)
    def test_defaults(self):
        params = _get_connection_params()
        assert params["host"] == "blacklist-postgres"
        assert params["port"] == 5432
        assert params["database"] == "blacklist"
        assert params["user"] == "postgres"
        assert params["password"] == "postgres"

    @patch.dict(
        "os.environ",
        {
            "POSTGRES_HOST": "myhost",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "mydb",
            "POSTGRES_USER": "myuser",
            "POSTGRES_PASSWORD": "mypass",
        },
        clear=True,
    )
    def test_individual_env_vars(self):
        params = _get_connection_params()
        assert params["host"] == "myhost"
        assert params["port"] == 5433
        assert params["database"] == "mydb"
        assert params["user"] == "myuser"
        assert params["password"] == "mypass"

    @patch.dict(
        "os.environ",
        {"DATABASE_URL": "postgresql://admin:secret@db.example.com:5434/proddb"},
        clear=True,
    )
    def test_database_url_parsed(self):
        params = _get_connection_params()
        assert params["host"] == "db.example.com"
        assert params["port"] == 5434
        assert params["database"] == "proddb"
        assert params["user"] == "admin"
        assert params["password"] == "secret"

    @patch.dict(
        "os.environ",
        {"POSTGRES_URL": "postgresql://u:p@host2:5435/db2"},
        clear=True,
    )
    def test_postgres_url_fallback(self):
        params = _get_connection_params()
        assert params["host"] == "host2"
        assert params["port"] == 5435
        assert params["database"] == "db2"

    @patch.dict(
        "os.environ",
        {
            "DATABASE_URL": "postgresql://u1:p1@host1:5436/db1",
            "POSTGRES_URL": "postgresql://u2:p2@host2:5437/db2",
        },
        clear=True,
    )
    def test_database_url_takes_priority_over_postgres_url(self):
        params = _get_connection_params()
        assert params["host"] == "host1"
        assert params["database"] == "db1"

    @patch.dict(
        "os.environ",
        {"DATABASE_URL": "postgresql://localhost/mydb"},
        clear=True,
    )
    def test_url_with_defaults_for_missing_parts(self):
        params = _get_connection_params()
        assert params["host"] == "localhost"
        assert params["port"] == 5432
        assert params["database"] == "mydb"
        assert params["user"] == "postgres"
        assert params["password"] == "postgres"
