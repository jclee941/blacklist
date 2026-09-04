from unittest.mock import Mock, call, patch

import pytest

from app.core.services.database_service import DatabaseService


@pytest.mark.unit
class TestDatabaseService:
    def test_init_in_testing_mode_skips_pool_init(self, monkeypatch):
        monkeypatch.setenv("TESTING", "True")
        monkeypatch.delenv("USE_REAL_DB", raising=False)

        with patch.object(DatabaseService, "_initialize_pool_with_retry") as init_pool:
            service = DatabaseService()

        assert service.connection_pool is None
        init_pool.assert_not_called()

    def test_initialize_pool_with_retry_success(self, monkeypatch):
        monkeypatch.delenv("TESTING", raising=False)

        test_conn = Mock()
        test_cursor = Mock()
        test_conn.cursor.return_value = test_cursor

        pool_instance = Mock()
        pool_instance.getconn.return_value = test_conn

        with patch.object(DatabaseService, "_initialize_pool_with_retry"):
            service = DatabaseService()

        with patch("app.core.services.database_service.pool.ThreadedConnectionPool", return_value=pool_instance):
            service._initialize_pool_with_retry(max_retries=1, base_delay=0)

        assert pool_instance.getconn.call_count == 2
        assert test_cursor.execute.call_args_list[0] == call("SELECT 1")
        migration_sql = test_cursor.execute.call_args_list[1].args[0]
        assert "ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE" in migration_sql
        assert "ALTER COLUMN is_active SET NOT NULL" in migration_sql
        assert "ALTER TABLE blacklist_ips" in migration_sql
        assert "ON whitelist_ips(ip_address)" in migration_sql
        assert "ON blacklist_ips(ip_address, source)" in migration_sql
        assert "ALTER ROLE" not in migration_sql
        assert pool_instance.putconn.call_args_list == [call(test_conn), call(test_conn)]
        test_conn.commit.assert_called_once_with()

    def test_initialize_pool_with_retry_failure_raises(self, monkeypatch):
        monkeypatch.delenv("TESTING", raising=False)

        with patch.object(DatabaseService, "_initialize_pool_with_retry"):
            service = DatabaseService()

        with (
            patch(
                "app.core.services.database_service.pool.ThreadedConnectionPool",
                side_effect=Exception("db down"),
            ),
            patch("app.core.services.database_service.time.sleep") as sleep,
        ):
            with pytest.raises(Exception, match="db down"):
                service._initialize_pool_with_retry(max_retries=2, base_delay=0.01)

        assert sleep.call_count == 1

    def test_initialize_pool_with_retry_caps_startup_backoff_budget(self, monkeypatch):
        monkeypatch.delenv("TESTING", raising=False)

        with patch.object(DatabaseService, "_initialize_pool_with_retry"):
            service = DatabaseService()

        with (
            patch(
                "app.core.services.database_service.pool.ThreadedConnectionPool",
                side_effect=Exception("db down"),
            ),
            patch("app.core.services.database_service.time.sleep") as sleep,
        ):
            with pytest.raises(Exception, match="db down"):
                service._initialize_pool_with_retry(max_retries=100, base_delay=100)

        assert sleep.call_args_list == [call(1.0), call(2.0), call(4.0), call(8.0)]

    def test_get_connection_reinitializes_pool_when_missing(self):
        with patch.object(DatabaseService, "_initialize_pool_with_retry"):
            service = DatabaseService()

        conn = Mock()
        service.connection_pool = Mock(getconn=Mock(return_value=conn))
        service._initialize_pool_with_retry = Mock(side_effect=lambda *args, **kwargs: None)

        result = service.get_connection()

        assert result is conn

    def test_get_connection_retries_without_reinitializing_active_pool(self):
        with patch.object(DatabaseService, "_initialize_pool_with_retry"):
            service = DatabaseService()

        pool_mock = Mock()
        pool_mock.getconn.side_effect = [Exception("first"), Exception("second"), Mock()]
        service.connection_pool = pool_mock

        with (
            patch.object(service, "_initialize_pool_with_retry") as reinit,
            patch("app.core.services.database_service.time.sleep"),
        ):
            result = service.get_connection()

        assert result is not None
        reinit.assert_not_called()

    def test_return_connection_discards_stale_connection_through_pool(self):
        with patch.object(DatabaseService, "_initialize_pool_with_retry"):
            service = DatabaseService()

        conn = Mock()
        conn.closed = False
        service.connection_pool = Mock(putconn=Mock(side_effect=[Exception("stale"), None]))

        service.return_connection(conn)

        assert service.connection_pool.putconn.call_args_list == [call(conn), call(conn, close=True)]
        conn.close.assert_not_called()

    def test_query_executes_with_params_and_returns_dicts(self):
        with patch.object(DatabaseService, "_initialize_pool_with_retry"):
            service = DatabaseService()

        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [{"count": 1}, {"count": 2}]

        with patch.object(service, "get_connection", return_value=conn), patch.object(service, "return_connection"):
            result = service.query("SELECT * FROM t WHERE id = %s", (1,))

        cursor.execute.assert_called_once_with("SELECT * FROM t WHERE id = %s", (1,))
        assert result == [{"count": 1}, {"count": 2}]

    def test_execute_rolls_back_on_error(self):
        with patch.object(DatabaseService, "_initialize_pool_with_retry"):
            service = DatabaseService()

        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = Exception("write error")

        with (
            patch.object(service, "get_connection", return_value=conn),
            patch.object(service, "return_connection") as return_connection,
        ):
            with pytest.raises(Exception, match="write error"):
                service.execute("UPDATE t SET x = 1")

        conn.rollback.assert_called_once()
        return_connection.assert_called_once_with(conn)

    def test_execute_returns_connection_on_success(self):
        with patch.object(DatabaseService, "_initialize_pool_with_retry"):
            service = DatabaseService()

        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        cursor.rowcount = 1

        with (
            patch.object(service, "get_connection", return_value=conn),
            patch.object(service, "return_connection") as return_connection,
        ):
            result = service.execute("UPDATE t SET x = 1")

        assert result == 1
        return_connection.assert_called_once_with(conn)
