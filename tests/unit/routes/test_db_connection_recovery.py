"""Tests for core/database/connection_recovery.py — PostgreSQLConnectionManager."""

from unittest.mock import patch, MagicMock

from core.database.connection_recovery import PostgreSQLConnectionManager


class TestConnectionRecoveryParams:
    @patch.dict("os.environ", {}, clear=True)
    def test_defaults(self):
        mgr = PostgreSQLConnectionManager()
        p = mgr.connection_params
        assert p["host"] == "blacklist-postgres"
        assert p["port"] == 5432
        assert p["database"] == "blacklist"
        assert p["user"] == "postgres"
        assert p["password"] == "postgres"

    @patch.dict(
        "os.environ",
        {
            "POSTGRES_HOST": "h1",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "db1",
            "POSTGRES_USER": "u1",
            "POSTGRES_PASSWORD": "pw1",
        },
        clear=True,
    )
    def test_individual_env_vars(self):
        mgr = PostgreSQLConnectionManager()
        p = mgr.connection_params
        assert p["host"] == "h1"
        assert p["port"] == 5433
        assert p["database"] == "db1"
        assert p["user"] == "u1"
        assert p["password"] == "pw1"

    @patch.dict(
        "os.environ",
        {"DATABASE_URL": "postgresql://admin:secret@db.example.com:5434/proddb"},
        clear=True,
    )
    def test_database_url_parsed(self):
        mgr = PostgreSQLConnectionManager()
        p = mgr.connection_params
        assert p["host"] == "db.example.com"
        assert p["port"] == 5434
        assert p["database"] == "proddb"
        assert p["user"] == "admin"
        assert p["password"] == "secret"

    @patch.dict(
        "os.environ",
        {"POSTGRES_URL": "postgresql://u:p@host2:5435/db2"},
        clear=True,
    )
    def test_postgres_url_fallback(self):
        mgr = PostgreSQLConnectionManager()
        p = mgr.connection_params
        assert p["host"] == "host2"
        assert p["port"] == 5435
        assert p["database"] == "db2"

    @patch.dict(
        "os.environ",
        {
            "DATABASE_URL": "postgresql://u1:p1@host1:5436/db1",
            "POSTGRES_URL": "postgresql://u2:p2@host2:5437/db2",
        },
        clear=True,
    )
    def test_database_url_priority(self):
        mgr = PostgreSQLConnectionManager()
        p = mgr.connection_params
        assert p["host"] == "host1"
        assert p["database"] == "db1"

    @patch.dict(
        "os.environ",
        {"DATABASE_URL": "postgresql://localhost/mydb"},
        clear=True,
    )
    def test_url_missing_parts_use_defaults(self):
        mgr = PostgreSQLConnectionManager()
        p = mgr.connection_params
        assert p["host"] == "localhost"
        assert p["port"] == 5432
        assert p["database"] == "mydb"
        assert p["user"] == "postgres"
        assert p["password"] == "postgres"


class TestRecoveryGetConnection:
    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_recovery.psycopg2.connect")
    def test_returns_connection_on_success(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mgr = PostgreSQLConnectionManager()
        conn = mgr.get_connection()
        assert conn is mock_conn

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_recovery.psycopg2.connect")
    def test_returns_none_when_all_hosts_fail(self, mock_connect):
        mock_connect.side_effect = Exception("refused")
        mgr = PostgreSQLConnectionManager()
        conn = mgr.get_connection()
        assert conn is None

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_recovery.psycopg2.connect")
    def test_tries_fallback_hosts(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.side_effect = [Exception("fail"), mock_conn]
        mgr = PostgreSQLConnectionManager()
        conn = mgr.get_connection()
        assert conn is mock_conn
        assert mock_connect.call_count == 2

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_recovery.psycopg2.connect")
    def test_connect_timeout_is_5_seconds(self, mock_connect):
        mock_connect.return_value = MagicMock()
        mgr = PostgreSQLConnectionManager()
        mgr.get_connection()
        _, kwargs = mock_connect.call_args
        assert kwargs["connect_timeout"] == 5


class TestStatsWithFallback:
    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_recovery.psycopg2.connect")
    def test_disconnected_when_no_connection(self, mock_connect):
        mock_connect.side_effect = Exception("refused")
        mgr = PostgreSQLConnectionManager()
        stats = mgr.get_stats_with_fallback()
        assert stats["status"] == "disconnected"
        assert stats["tables"] == 0
        assert stats["connections"] == 0

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_recovery.psycopg2.connect")
    def test_connected_with_valid_query(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(12,), (4,)]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.get_dsn_parameters.return_value = {"host": "db1"}
        mock_connect.return_value = mock_conn

        mgr = PostgreSQLConnectionManager()
        stats = mgr.get_stats_with_fallback()

        assert stats["status"] == "connected"
        assert stats["tables"] == 12
        assert stats["connections"] == 4
        assert stats["host"] == "db1"

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_recovery.psycopg2.connect")
    def test_error_status_on_query_failure(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("query failed")
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_connect.return_value = mock_conn

        mgr = PostgreSQLConnectionManager()
        stats = mgr.get_stats_with_fallback()

        assert stats["status"] == "error"
        assert "query failed" in stats["message"]

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_recovery.psycopg2.connect")
    def test_connection_closed_after_query(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(5,), (2,)]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.get_dsn_parameters.return_value = {"host": "db1"}
        mock_connect.return_value = mock_conn

        mgr = PostgreSQLConnectionManager()
        mgr.get_stats_with_fallback()

        mock_conn.close.assert_called_once()
