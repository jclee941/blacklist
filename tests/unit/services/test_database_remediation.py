from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from psycopg2 import pool

from core.routes.api.ip_management.repository import IPManagementRepository
from core.services.analytics_service import AnalyticsService
from core.services.collection.collection_history import CollectionHistoryManager
from core.services.collection.collection_status import CollectionStatusManager
from core.services.database_service import DatabaseService
from core.services.expiry_service import IPExpiryService
from core.services.optimized_blacklist_service import OptimizedBlacklistService
from core.services.scheduler_service import CollectionScheduler


class OperationFailedError(RuntimeError):
    pass


def make_database_service() -> DatabaseService:
    with patch.object(DatabaseService, "_initialize_pool_with_retry"):
        return DatabaseService()


def test_connection_lease_returns_connection_after_success() -> None:
    # Given
    service = make_database_service()
    raw_connection = MagicMock()
    connection_pool = MagicMock()
    connection_pool.getconn.return_value = raw_connection
    service.connection_pool = connection_pool

    # When
    with service.connection() as connection:
        assert connection is raw_connection

    # Then
    connection_pool.putconn.assert_called_once_with(raw_connection)


def test_connection_lease_rolls_back_and_returns_connection_after_exception() -> None:
    # Given
    service = make_database_service()
    raw_connection = MagicMock()
    connection_pool = MagicMock()
    connection_pool.getconn.return_value = raw_connection
    service.connection_pool = connection_pool

    # When
    with pytest.raises(OperationFailedError, match="operation failed"):
        with service.connection():
            raise OperationFailedError("operation failed")

    # Then
    raw_connection.rollback.assert_called_once_with()
    connection_pool.putconn.assert_called_once_with(raw_connection)


def test_get_connection_does_not_reinitialize_active_pool_when_exhausted() -> None:
    # Given
    service = make_database_service()
    connection_pool = MagicMock()
    connection_pool.getconn.side_effect = pool.PoolError("connection pool exhausted")
    service.connection_pool = connection_pool

    # When
    with (
        patch.object(service, "_initialize_pool_with_retry") as initialize_pool,
        patch("core.services.database_service.time.sleep"),
        pytest.raises(pool.PoolError, match="exhausted"),
    ):
        service.get_connection()

    # Then
    initialize_pool.assert_not_called()
    connection_pool.closeall.assert_not_called()


@pytest.mark.parametrize("method_name", ["query", "health_check"])
def test_database_read_paths_return_connection_when_cursor_raises(method_name: str) -> None:
    # Given
    service = make_database_service()
    raw_connection = MagicMock()
    raw_connection.cursor.return_value.execute.side_effect = RuntimeError("query failed")
    connection_pool = MagicMock()
    connection_pool.getconn.return_value = raw_connection
    service.connection_pool = connection_pool

    # When
    if method_name == "query":
        with pytest.raises(RuntimeError, match="query failed"):
            service.query("SELECT 1")
    else:
        assert service.health_check() is False

    # Then
    connection_pool.putconn.assert_called_once_with(raw_connection)


def test_collection_status_consumes_source_rows_once() -> None:
    # Given
    app = Flask(__name__)
    db_service = MagicMock()
    connection = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (2,)
    cursor.fetchall.return_value = [("REGTECH", 2)]
    connection.cursor.return_value = cursor
    db_service.get_connection.return_value = connection
    app.extensions["db_service"] = db_service
    manager = CollectionStatusManager()

    # When
    with app.app_context():
        result = manager._get_database_stats()

    # Then
    assert result == {"total_ips": 2, "sources": {"REGTECH": 2}}
    cursor.fetchall.assert_called_once_with()
    db_service.return_connection.assert_called_once_with(connection)


def test_analytics_groups_the_selected_source_column() -> None:
    # Given
    db_service = MagicMock()
    db_service.query.return_value = []
    service = AnalyticsService(db_service=db_service)

    # When
    result = service.analyze_false_positive_patterns()

    # Then
    assert result["success"] is True
    source_query = db_service.query.call_args_list[1].args[0]
    assert "SELECT\n                    source," in source_query
    assert "GROUP BY source" in source_query


def test_manual_expiry_uses_write_execution_path() -> None:
    # Given
    db_service = MagicMock()
    db_service.query.return_value = [{"id": 7, "ip_address": "192.0.2.7", "source": "MANUAL", "is_active": True}]
    db_service.execute.return_value = 1
    service = IPExpiryService(db_service=db_service)

    # When
    result = service.manually_expire_ip("192.0.2.7")

    # Then
    assert result["success"] is True
    db_service.execute.assert_called_once()
    db_service.query.assert_called_once()


def test_unified_statistics_uses_base_tables_with_stable_result_shape() -> None:
    # Given
    db_service = MagicMock()
    connection = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        {"list_type": "blacklist", "source": "REGTECH", "count": 4, "active_count": 3, "last_updated": None}
    ]
    connection.cursor.return_value = cursor
    db_service.get_connection.return_value = connection
    repository = IPManagementRepository(db_service)

    # When
    result = repository.get_statistics()

    # Then
    query = cursor.execute.call_args.args[0]
    assert "unified_ip_statistics" not in query
    assert "FROM blacklist_ips" in query
    assert "FROM whitelist_ips" in query
    assert result[0]["active_count"] == 3
    db_service.return_connection.assert_called_once_with(connection)


def test_collection_status_query_uses_current_history_columns() -> None:
    # Given
    db_service = MagicMock()
    connection = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.side_effect = [[], []]
    connection.cursor.return_value = cursor
    db_service.get_connection.return_value = connection
    service = OptimizedBlacklistService(db_service)

    # When
    result = service.get_collection_status()

    # Then
    history_query = cursor.execute.call_args_list[0].args[0]
    assert "items_collected AS ips_collected" in history_query
    assert "collection_date" in history_query
    assert "WHERE created_at" not in history_query
    assert result["success"] is True
    db_service.return_connection.assert_called_once_with(connection)


def test_collection_history_cleanup_filters_on_collection_date() -> None:
    # Given
    app = Flask(__name__)
    db_service = MagicMock()
    connection = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = 2
    connection.cursor.return_value = cursor
    db_service.get_connection.return_value = connection
    app.extensions["db_service"] = db_service
    manager = CollectionHistoryManager()

    # When
    with app.app_context():
        deleted = manager.cleanup_old_history()

    # Then
    assert deleted == 2
    cleanup_query = cursor.execute.call_args.args[0]
    assert "WHERE collection_date < %s" in cleanup_query
    db_service.return_connection.assert_called_once_with(connection)


def test_expiry_scheduler_records_history_with_current_columns() -> None:
    # Given
    db_service = MagicMock()
    connection = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = [(9, "192.0.2.9", None, "REGTECH")]
    cursor.rowcount = 1
    connection.cursor.return_value = cursor
    db_service.get_connection.return_value = connection
    scheduler = CollectionScheduler(db_service=db_service)

    # When
    scheduler._deactivate_expired_ips()

    # Then
    history_query = cursor.execute.call_args_list[2].args[0]
    assert "service_name" in history_query
    assert "items_collected" in history_query
    assert "details" in history_query
    assert "collection_type" not in history_query
