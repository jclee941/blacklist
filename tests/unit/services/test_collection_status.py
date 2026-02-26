"""Unit tests for CollectionStatusManager"""

import pytest
from unittest.mock import Mock, patch


@pytest.mark.unit
class TestCollectionStatusManager:
    """Tests for CollectionStatusManager — pure state management methods"""

    def setup_method(self):
        """Setup test fixtures"""
        from app.core.services.collection.collection_status import CollectionStatusManager

        self.manager = CollectionStatusManager()

    # --- start_collection ---

    def test_start_collection_success(self):
        """Start collection for existing type"""
        result = self.manager.start_collection("regtech")
        assert result is True
        assert "regtech" in self.manager.active_collections

    def test_start_collection_already_running(self):
        """Start collection when already running returns False"""
        self.manager.active_collections.add("regtech")
        result = self.manager.start_collection("regtech")
        assert result is False

    def test_start_collection_updates_status(self):
        """Start collection updates status dict"""
        self.manager.start_collection("regtech")
        assert self.manager.collection_status["regtech"]["running"] is True

    # --- stop_collection ---

    def test_stop_collection_success(self):
        """Stop running collection"""
        self.manager.active_collections.add("regtech")
        self.manager.collection_status["regtech"] = {"running": True}

        result = self.manager.stop_collection("regtech")

        assert result is True
        assert "regtech" not in self.manager.active_collections
        assert self.manager.collection_status["regtech"]["running"] is False

    def test_stop_collection_not_running(self):
        """Stop when not running returns False"""
        result = self.manager.stop_collection("regtech")
        assert result is False

    # --- stop_all_collections ---

    def test_stop_all_collections(self):
        """Stop all active collections"""
        self.manager.active_collections.add("regtech")
        self.manager.active_collections.add("secudium")
        self.manager.collection_status["regtech"] = {"running": True}
        self.manager.collection_status["secudium"] = {"running": True}

        result = self.manager.stop_all_collections()

        assert len(self.manager.active_collections) == 0
        # Return format: {'success': True, 'stopped_collections': [...], 'message': '...'}
        assert result.get("success") is True
        assert "stopped_collections" in result

    def test_stop_all_no_active(self):
        """Stop all when none active"""
        result = self.manager.stop_all_collections()
        assert result is not None

    # --- update_collection_error ---

    def test_update_collection_error(self):
        """Error state recorded correctly for existing type"""
        self.manager.collection_status["regtech"] = {"running": True}

        self.manager.update_collection_error("regtech", "Connection timeout")

        status = self.manager.collection_status["regtech"]
        assert status["running"] is False
        assert status["last_error"] == "Connection timeout"

    def test_update_collection_error_secudium(self):
        """Error state recorded correctly for secudium type"""
        self.manager.collection_status["secudium"] = {"running": True}

        self.manager.update_collection_error("secudium", "Auth failed")

        status = self.manager.collection_status["secudium"]
        assert status["running"] is False
        assert status["last_error"] == "Auth failed"

    # --- get_collection_status (with mocked DB) ---

    def test_get_collection_status_with_mock_app(self):
        """Collection status returns combined data"""
        mock_app = Mock()
        mock_db = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {"count": 0}
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        mock_app.extensions = {"db_service": mock_db}

        with patch("app.core.services.collection.collection_status.current_app", mock_app):
            with patch.object(self.manager, "_check_collector_container", return_value={"status": "healthy"}):
                result = self.manager.get_collection_status()

                assert isinstance(result, dict)
