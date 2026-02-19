"""Tests for core/database/connection_pool_manager.py — SmartConnectionManager."""

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from core.database.connection_pool_manager import SmartConnectionManager


class TestSmartConnectionManagerParams:
    """_get_connection_params env-var parsing."""

    @patch.dict("os.environ", {}, clear=True)
    def test_defaults(self):
        mgr = SmartConnectionManager()
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
        mgr = SmartConnectionManager()
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
        mgr = SmartConnectionManager()
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
        mgr = SmartConnectionManager()
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
        mgr = SmartConnectionManager()
        p = mgr.connection_params
        assert p["host"] == "host1"
        assert p["database"] == "db1"
        assert p["user"] == "u1"

    @patch.dict(
        "os.environ",
        {"DATABASE_URL": "postgresql://localhost/mydb"},
        clear=True,
    )
    def test_url_missing_parts_use_defaults(self):
        mgr = SmartConnectionManager()
        p = mgr.connection_params
        assert p["host"] == "localhost"
        assert p["port"] == 5432
        assert p["database"] == "mydb"
        assert p["user"] == "postgres"
        assert p["password"] == "postgres"


class TestErrorSuppression:
    """_should_suppress_error_logging and _log_connection_error."""

    @patch.dict("os.environ", {}, clear=True)
    def test_first_error_not_suppressed(self):
        mgr = SmartConnectionManager()
        assert mgr._should_suppress_error_logging() is False

    @patch.dict("os.environ", {}, clear=True)
    def test_suppressed_after_max_errors_within_backoff(self):
        mgr = SmartConnectionManager()
        mgr._error_count = 5
        mgr._last_error_time = datetime.now()
        assert mgr._should_suppress_error_logging() is True

    @patch.dict("os.environ", {}, clear=True)
    def test_not_suppressed_below_max_errors(self):
        mgr = SmartConnectionManager()
        mgr._error_count = 3
        mgr._last_error_time = datetime.now()
        assert mgr._should_suppress_error_logging() is False

    @patch.dict("os.environ", {}, clear=True)
    def test_counter_resets_after_backoff_expires(self):
        mgr = SmartConnectionManager()
        mgr._error_count = 10
        mgr._last_error_time = datetime.now() - timedelta(seconds=61)
        result = mgr._should_suppress_error_logging()
        assert result is False
        assert mgr._error_count == 0

    @patch.dict("os.environ", {}, clear=True)
    def test_log_connection_error_increments_count(self):
        mgr = SmartConnectionManager()
        err = Exception("connection refused")
        mgr._log_connection_error(err, "testhost")
        assert mgr._error_count == 1
        assert mgr._last_error_time is not None

    @patch.dict("os.environ", {}, clear=True)
    def test_log_connection_error_suppressed_after_max(self):
        mgr = SmartConnectionManager()
        err = Exception("connection refused")
        for _ in range(5):
            mgr._log_connection_error(err, "testhost")
        assert mgr._error_count == 5
        mgr._log_connection_error(err, "testhost")
        assert mgr._error_count == 5


class TestGetConnection:
    """get_connection with mocked psycopg2."""

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_pool_manager.psycopg2.connect")
    def test_returns_connection_on_success(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mgr = SmartConnectionManager()
        conn = mgr.get_connection()
        assert conn is mock_conn
        assert mgr._error_count == 0

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_pool_manager.psycopg2.connect")
    def test_resets_error_counter_on_success(self, mock_connect):
        mock_connect.return_value = MagicMock()
        mgr = SmartConnectionManager()
        mgr._error_count = 3
        mgr._last_error_time = datetime.now()
        mgr.get_connection()
        assert mgr._error_count == 0
        assert mgr._last_error_time is None

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_pool_manager.psycopg2.connect")
    def test_returns_none_when_all_hosts_fail(self, mock_connect):
        mock_connect.side_effect = Exception("refused")
        mgr = SmartConnectionManager()
        conn = mgr.get_connection()
        assert conn is None

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_pool_manager.psycopg2.connect")
    def test_tries_multiple_hosts(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.side_effect = [Exception("fail"), mock_conn]
        mgr = SmartConnectionManager()
        conn = mgr.get_connection()
        assert conn is mock_conn
        assert mock_connect.call_count == 2


class TestGracefulDegradation:
    """get_stats_with_graceful_degradation caching and fallback."""

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_pool_manager.psycopg2.connect")
    def test_fallback_when_no_connection_no_cache(self, mock_connect):
        mock_connect.side_effect = Exception("refused")
        mgr = SmartConnectionManager()
        stats = mgr.get_stats_with_graceful_degradation()
        assert stats["status"] == "degraded"
        assert stats["tables"] == 0
        assert stats["connections"] == 0

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_pool_manager.psycopg2.connect")
    def test_returns_cached_data_when_connection_fails(self, mock_connect):
        mock_connect.side_effect = Exception("refused")
        mgr = SmartConnectionManager()
        mgr._cached_stats = {
            "data": {"status": "connected", "tables": 10, "connections": 5, "host": "db1"},
            "cached_at": datetime.now() - timedelta(seconds=400),
        }
        stats = mgr.get_stats_with_graceful_degradation()
        assert stats["status"] == "degraded"
        assert stats["tables"] == 10
        assert stats["connections"] == 5

    @patch.dict("os.environ", {}, clear=True)
    def test_returns_fresh_cache_without_reconnecting(self):
        mgr = SmartConnectionManager()
        mgr._cached_stats = {
            "data": {"status": "connected", "tables": 20, "connections": 8},
            "cached_at": datetime.now() - timedelta(seconds=100),
        }
        stats = mgr.get_stats_with_graceful_degradation()
        assert stats["status"] == "connected"
        assert stats["tables"] == 20

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_pool_manager.psycopg2.connect")
    def test_successful_query_updates_cache(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(15,), (3,)]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.get_dsn_parameters.return_value = {"host": "db1"}
        mock_connect.return_value = mock_conn

        mgr = SmartConnectionManager()
        stats = mgr.get_stats_with_graceful_degradation()

        assert stats["status"] == "connected"
        assert stats["tables"] == 15
        assert stats["connections"] == 3
        assert mgr._cached_stats is not None
        assert mgr._cached_stats["data"]["tables"] == 15

    @patch.dict("os.environ", {}, clear=True)
    @patch("core.database.connection_pool_manager.psycopg2.connect")
    def test_query_error_returns_error_status(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("query failed")
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_connect.return_value = mock_conn

        mgr = SmartConnectionManager()
        stats = mgr.get_stats_with_graceful_degradation()

        assert stats["status"] == "error"
        assert "query failed" in stats["message"]
