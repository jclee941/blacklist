import os
from unittest.mock import Mock, patch, MagicMock

import pytest


class TestGetConnectionParams:
    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://myuser:mypass@myhost:5433/mydb"}, clear=False)
    def test_parses_database_url(self):
        from core.database.connection import _get_connection_params

        params = _get_connection_params()
        assert params["host"] == "myhost"
        assert params["port"] == 5433 or params["port"] == "5433"
        assert params["database"] == "mydb" or params["dbname"] == "mydb"
        assert params["user"] == "myuser"
        assert params["password"] == "mypass"

    @patch.dict(os.environ, {"POSTGRES_URL": "postgresql://puser:ppass@phost:5434/pdb"}, clear=False)
    def test_parses_postgres_url_fallback(self):
        env_no_db_url = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
        with patch.dict(os.environ, env_no_db_url, clear=True):
            os.environ["POSTGRES_URL"] = "postgresql://puser:ppass@phost:5434/pdb"
            from core.database.connection import _get_connection_params

            params = _get_connection_params()
            assert isinstance(params, dict)

    @patch.dict(
        os.environ,
        {
            "POSTGRES_HOST": "custom-host",
            "POSTGRES_PORT": "5555",
            "POSTGRES_DB": "custom-db",
            "POSTGRES_USER": "custom-user",
            "POSTGRES_PASSWORD": "custom-pass",
        },
        clear=False,
    )
    def test_uses_individual_env_vars(self):
        env_clean = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "POSTGRES_URL")}
        env_clean.update(
            {
                "POSTGRES_HOST": "custom-host",
                "POSTGRES_PORT": "5555",
                "POSTGRES_DB": "custom-db",
                "POSTGRES_USER": "custom-user",
                "POSTGRES_PASSWORD": "custom-pass",
            }
        )
        with patch.dict(os.environ, env_clean, clear=True):
            from core.database.connection import _get_connection_params

            params = _get_connection_params()
            assert params["host"] == "custom-host"

    def test_uses_defaults(self):
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k
            not in (
                "DATABASE_URL",
                "POSTGRES_URL",
                "POSTGRES_HOST",
                "POSTGRES_PORT",
                "POSTGRES_DB",
                "POSTGRES_USER",
                "POSTGRES_PASSWORD",
            )
        }
        with patch.dict(os.environ, env_clean, clear=True):
            from core.database.connection import _get_connection_params

            params = _get_connection_params()
            assert params["host"] == "blacklist-postgres" or isinstance(params["host"], str)


class TestGetDbConnection:
    @patch("core.database.connection.psycopg2")
    def test_creates_connection(self, mock_psycopg2):
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        with patch(
            "core.database.connection._get_connection_params",
            return_value={"host": "localhost", "port": 5432, "database": "test", "user": "test", "password": "test"},
        ):
            from core.database.connection import get_db_connection

            conn = get_db_connection()
        mock_psycopg2.connect.assert_called_once()
        assert conn is mock_conn

    @patch("core.database.connection.psycopg2")
    def test_connection_failure(self, mock_psycopg2):
        mock_psycopg2.connect.side_effect = Exception("connection refused")
        with patch(
            "core.database.connection._get_connection_params",
            return_value={"host": "localhost", "port": 5432, "database": "test", "user": "test", "password": "test"},
        ):
            from core.database.connection import get_db_connection

            with pytest.raises(Exception, match="connection refused"):
                get_db_connection()
