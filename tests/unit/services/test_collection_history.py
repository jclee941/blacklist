"""Unit tests for CollectionHistoryManager"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime


@pytest.mark.unit
class TestCollectionHistoryManager:
    """Tests for CollectionHistoryManager"""

    def setup_method(self):
        """Setup test fixtures"""
        from app.core.services.collection.collection_history import CollectionHistoryManager

        self.manager = CollectionHistoryManager()
        self.mock_db = Mock()
        self.mock_app = Mock()
        self.mock_app.extensions = {"db_service": self.mock_db}

    def _mock_cursor_conn(self, fetchone=None, fetchall=None, rowcount=0):
        """Helper to create mock conn/cursor matching the actual DB pattern."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = fetchone
        mock_cursor.fetchall.return_value = fetchall or []
        mock_cursor.rowcount = rowcount
        self.mock_db.get_connection.return_value = mock_conn
        return mock_conn, mock_cursor

    # --- record_collection_history ---

    def test_record_history_success(self):
        """History record saved"""
        self._mock_cursor_conn()

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.record_collection_history(
                collection_type="regtech",
                collected_count=150,
                success=True,
                execution_time_ms=3500,
            )

        assert result is True

    def test_record_history_db_error(self):
        """History record fails gracefully"""
        self.mock_db.get_connection.side_effect = Exception("Insert failed")

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.record_collection_history(
                collection_type="regtech",
                collected_count=0,
                success=False,
                error_message="Connection timeout",
            )

        assert result is False

    def test_record_history_with_dates(self):
        """History record includes date range"""
        self._mock_cursor_conn()

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.record_collection_history(
                collection_type="regtech",
                collected_count=50,
                start_date="2025-01-01",
                end_date="2025-01-15",
                success=True,
            )

        assert result is True

    # --- get_recent_history ---

    def test_get_recent_history_success(self):
        """Recent history returned"""
        # Cursor returns TUPLES — dict(zip(columns, row)) maps them
        # columns: service_name, items_collected, start_date, end_date, details, collection_date
        history_data = [
            ("REGTECH", 100, datetime(2025, 1, 15), datetime(2025, 1, 16), None, datetime(2025, 1, 15)),
        ]
        mock_conn, _ = self._mock_cursor_conn(fetchall=history_data)

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.get_recent_history()

        assert len(result) == 1
        assert result[0]["service_name"] == "REGTECH"
        self.mock_db.return_connection.assert_called_once_with(mock_conn)

    def test_get_recent_history_returns_connection_after_query_error(self):
        mock_conn, mock_cursor = self._mock_cursor_conn()
        mock_cursor.execute.side_effect = Exception("Query failed")

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.get_recent_history()

        assert result == []
        self.mock_db.return_connection.assert_called_once_with(mock_conn)

    def test_get_recent_history_with_type_filter(self):
        """History filtered by collection type"""
        self._mock_cursor_conn(fetchall=[])

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.get_recent_history(collection_type="regtech")

        assert result == []

    def test_get_recent_history_custom_days(self):
        """History respects days parameter"""
        self._mock_cursor_conn(fetchall=[])

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.get_recent_history(days=7)

        assert result == []

    def test_get_recent_history_db_error(self):
        """DB error returns empty list"""
        self.mock_db.get_connection.side_effect = Exception("Query failed")

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.get_recent_history()

        assert result == []

    # --- get_collection_statistics ---

    def test_get_statistics_success(self):
        """Collection statistics returned"""
        # Mock 3 sequential DB queries: totals, last_7_days, by_type
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [
            {"total_collections": 500, "total_collected_items": 10000},  # totals query
        ]
        mock_cursor.fetchall.side_effect = [
            [{"date": "2025-01-15", "count": 50}],  # last_7_days
            [{"service_name": "REGTECH", "count": 400}],  # by_type
        ]
        self.mock_db.get_connection.return_value = mock_conn

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.get_collection_statistics()

        assert result is not None
        assert isinstance(result, dict)

    def test_get_statistics_db_error(self):
        """Statistics error handled"""
        self.mock_db.get_connection.side_effect = Exception("DB down")

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.get_collection_statistics()

        # Should return empty/error result, not raise
        assert result is not None

    # --- cleanup_old_history ---

    def test_cleanup_old_history(self):
        """Old history records deleted"""
        mock_conn, mock_cursor = self._mock_cursor_conn(rowcount=15)

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.cleanup_old_history()

        assert result == 15

    def test_cleanup_old_history_none_deleted(self):
        """No old records to delete"""
        self._mock_cursor_conn(rowcount=0)

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.cleanup_old_history()

        assert result == 0

    def test_cleanup_old_history_db_error(self):
        """Cleanup error returns 0"""
        self.mock_db.get_connection.side_effect = Exception("Delete failed")

        with patch("app.core.services.collection.collection_history.current_app", self.mock_app):
            result = self.manager.cleanup_old_history()

        assert result == 0
