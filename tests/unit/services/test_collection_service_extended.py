"""Extended tests for collection_service uncovered methods."""

from unittest.mock import Mock, MagicMock, patch
from core.services.collection_service import CollectionService


class TestCollectionServiceExtended:
    def _make_service(self):
        mock_db = Mock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        svc = CollectionService(db_service=mock_db)
        return svc, mock_db, mock_conn, mock_cursor

    def test_trigger_regtech_collection_success(self):
        svc, _, _, _ = self._make_service()
        svc.active_collections = set()
        mock_validator = MagicMock()
        mock_validator.validate_collection_request.return_value = (True, "ok")
        mock_status_mgr = MagicMock()
        mock_regtech = MagicMock()
        mock_regtech.collect_regtech_ips.return_value = [{"ip_address": "1.1.1.1"}]
        mock_history = MagicMock()

        with (
            patch.object(svc, "validator", mock_validator, create=True),
            patch.object(svc, "status_manager", mock_status_mgr, create=True),
            patch.object(svc, "regtech_collector", mock_regtech, create=True),
            patch.object(svc, "history_manager", mock_history, create=True),
        ):
            result = svc.trigger_regtech_collection(start_date="2024-01-01", end_date="2024-01-31")
        assert result.get("success") is True or "error" not in result

    def test_trigger_regtech_collection_already_running(self):
        svc, _, _, _ = self._make_service()
        svc.active_collections = {"regtech"}
        result = svc.trigger_regtech_collection(start_date="2024-01-01", end_date="2024-01-31")
        assert "already" in str(result).lower() or result.get("success") is False

    def test_trigger_regtech_with_credentials(self):
        svc, _, _, _ = self._make_service()
        svc.active_collections = set()
        mock_validator = MagicMock()
        mock_validator.validate_collection_request.return_value = (True, "ok")
        mock_status_mgr = MagicMock()
        mock_regtech = MagicMock()
        mock_regtech.collect_real_regtech_data.return_value = [{"ip_address": "2.2.2.2"}]
        mock_history = MagicMock()

        with (
            patch.object(svc, "validator", mock_validator, create=True),
            patch.object(svc, "status_manager", mock_status_mgr, create=True),
            patch.object(svc, "regtech_collector", mock_regtech, create=True),
            patch.object(svc, "history_manager", mock_history, create=True),
        ):
            svc.trigger_regtech_collection(
                start_date="2024-01-01", end_date="2024-01-31", username="user", password="pass"
            )

    def test_trigger_regtech_collection_exception(self):
        svc, _, _, _ = self._make_service()
        svc.active_collections = set()
        mock_validator = MagicMock()
        mock_validator.validate_collection_request.side_effect = Exception("boom")

        with patch.object(svc, "validator", mock_validator, create=True):
            result = svc.trigger_regtech_collection(start_date="2024-01-01", end_date="2024-01-31")
        assert result.get("success") is False or "error" in str(result).lower()

    def test_trigger_all_collections(self):
        svc, _, _, _ = self._make_service()
        svc.active_collections = set()
        with patch.object(svc, "trigger_collection", return_value={"success": True, "count": 5}):
            result = svc.trigger_all_collections()
        assert isinstance(result, dict)

    def test_trigger_all_collections_exception(self):
        svc, _, _, _ = self._make_service()
        with patch.object(svc, "trigger_collection", side_effect=Exception("boom")):
            result = svc.trigger_all_collections()
        assert result.get("success") is False or "error" in str(result).lower()

    def test_stop_all_collections(self):
        svc, _, _, _ = self._make_service()
        svc.active_collections = {"regtech"}
        mock_status_mgr = MagicMock()
        with patch.object(svc, "status_manager", mock_status_mgr, create=True):
            svc.stop_all_collections()
        assert len(svc.active_collections) == 0

    def test_stop_all_collections_exception(self):
        svc, _, _, _ = self._make_service()
        mock_status_mgr = MagicMock()
        mock_status_mgr.stop_all_collections.side_effect = Exception("boom")
        with patch.object(svc, "status_manager", mock_status_mgr, create=True):
            svc.stop_all_collections()

    def test_get_collection_stats_success(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.fetchone.return_value = {
            "total_ips": 100,
            "active_ips": 80,
            "sources": 3,
            "latest_collection": "2024-01-01",
        }
        result = svc.get_collection_stats()
        assert isinstance(result, dict)

    def test_get_collection_stats_exception(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_db.get_connection.side_effect = Exception("DB error")
        result = svc.get_collection_stats()
        assert result.get("success") is False or "error" in str(result).lower()

    def test_collect_regtech_ips(self):
        svc, _, _, _ = self._make_service()
        mock_regtech = MagicMock()
        mock_regtech.collect_regtech_ips.return_value = [{"ip": "1.1.1.1"}]
        with patch.object(svc, "regtech_collector", mock_regtech, create=True):
            result = svc._collect_regtech_ips()
        assert isinstance(result, list)

    def test_save_collection_data_exception(self):
        svc, mock_db, mock_conn, mock_cursor = self._make_service()
        mock_cursor.execute.side_effect = Exception("DB error")
        svc._save_collection_data([{"ip_address": "1.1.1.1"}], "REGTECH")
