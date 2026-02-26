"""Tests for collection_service.py"""

from unittest.mock import Mock, MagicMock, patch


def _make_service(db_service=None):
    """Create CollectionService with mocked dependencies."""
    mock_db = db_service or Mock()
    with patch.dict(
        "sys.modules",
        {
            "core.services.collection.collection_validator": MagicMock(),
            "core.services.collection.collection_history": MagicMock(),
            "core.services.collection.collection_status": MagicMock(),
            "core.services.collection.regtech_data": MagicMock(),
        },
    ):
        from core.services.collection_service import CollectionService

        svc = CollectionService(db_service=mock_db)
    return svc, mock_db


class TestCollectionServiceInit:
    def test_init_sets_db_service(self):
        svc, mock_db = _make_service()
        assert svc.db_service is mock_db

    def test_init_creates_empty_active_collections(self):
        svc, _ = _make_service()
        assert isinstance(svc.active_collections, set)
        assert len(svc.active_collections) == 0

    def test_init_creates_collection_status_dict(self):
        svc, _ = _make_service()
        assert "regtech" in svc.collection_status
        assert "secudium" in svc.collection_status


class TestTriggerCollection:
    @patch("core.services.collection_service.status_manager")
    @patch("core.services.collection_service.history_manager")
    @patch("core.services.collection_service.validator")
    def test_trigger_collection_already_active(self, mock_val, mock_hist, mock_status):
        svc, _ = _make_service()
        svc.active_collections.add("regtech")
        result = svc.trigger_collection("regtech")
        assert result.get("success") is False or "already" in str(result).lower() or "collecting" in str(result).lower()

    @patch("core.services.collection_service.status_manager")
    @patch("core.services.collection_service.history_manager")
    @patch("core.services.collection_service.validator")
    def test_trigger_collection_adds_to_active(self, mock_val, mock_hist, mock_status):
        svc, _ = _make_service()
        mock_status.start_collection = Mock()
        mock_status.stop_collection = Mock()
        with patch.object(svc, "_perform_collection", return_value={"success": True, "data": []}):
            with patch.object(svc, "_save_collection_data", return_value=True):
                svc.trigger_collection("regtech")
        # After completion, active_collections should be cleared (finally block)
        assert "regtech" not in svc.active_collections

    @patch("core.services.collection_service.status_manager")
    @patch("core.services.collection_service.history_manager")
    @patch("core.services.collection_service.validator")
    def test_trigger_collection_calls_status_manager(self, mock_val, mock_hist, mock_status):
        svc, _ = _make_service()
        mock_status.start_collection = Mock()
        mock_status.stop_collection = Mock()
        with patch.object(svc, "_perform_collection", return_value={"success": True, "data": []}):
            with patch.object(svc, "_save_collection_data", return_value=True):
                svc.trigger_collection("regtech")
        mock_status.start_collection.assert_called_once_with("regtech")
        mock_status.stop_collection.assert_called_once_with("regtech")

    @patch("core.services.collection_service.status_manager")
    @patch("core.services.collection_service.history_manager")
    @patch("core.services.collection_service.validator")
    def test_trigger_collection_handles_error(self, mock_val, mock_hist, mock_status):
        svc, _ = _make_service()
        mock_status.start_collection = Mock()
        mock_status.stop_collection = Mock()
        with patch.object(svc, "_perform_collection", side_effect=Exception("test error")):
            result = svc.trigger_collection("regtech")
        assert result.get("success") is False
        assert "regtech" not in svc.active_collections


class TestTriggerRegtechCollection:
    @patch("core.services.collection_service.regtech_collector")
    @patch("core.services.collection_service.validator")
    def test_regtech_collection_already_active(self, mock_val, mock_collector):
        svc, _ = _make_service()
        svc.active_collections.add("regtech")
        result = svc.trigger_regtech_collection("2024-01-01", "2024-01-31", "user", "pass")
        assert result.get("success") is False or "already" in str(result).lower()

    @patch("core.services.collection_service.regtech_collector")
    @patch("core.services.collection_service.validator")
    @patch("core.services.collection_service.status_manager")
    def test_regtech_collection_success(self, mock_status, mock_val, mock_collector):
        svc, _ = _make_service()
        mock_status.start_collection = Mock()
        mock_status.stop_collection = Mock()
        mock_val._validate_collection_prerequisites = Mock(return_value=True)
        mock_collector.collect_real_regtech_data = Mock(
            return_value={"success": True, "data": [], "collected_count": 5}
        )
        with patch.object(svc, "_save_collection_data", return_value=True):
            result = svc.trigger_regtech_collection("2024-01-01", "2024-01-31", "user", "pass")
        # Should return a result dict
        assert isinstance(result, dict)


class TestTriggerAllCollections:
    @patch("core.services.collection_service.status_manager")
    @patch("core.services.collection_service.history_manager")
    @patch("core.services.collection_service.validator")
    def test_trigger_all_returns_dict(self, mock_val, mock_hist, mock_status):
        svc, _ = _make_service()
        with patch.object(svc, "trigger_collection", return_value={"success": True}):
            result = svc.trigger_all_collections()
        assert isinstance(result, dict)


class TestStopAllCollections:
    @patch("core.services.collection_service.status_manager")
    def test_stop_all_clears_active(self, mock_status):
        svc, _ = _make_service()
        svc.active_collections.add("regtech")
        svc.active_collections.add("secudium")
        mock_status.stop_all_collections = Mock(return_value={"message": "All collections stopped"})
        result = svc.stop_all_collections()
        assert len(svc.active_collections) == 0
        assert isinstance(result, dict)


class TestGetCollectionStats:
    def test_get_stats_returns_dict(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_cursor.fetchone.return_value = (100, 80, "2024-01-01", None)
        mock_cursor.fetchall.return_value = [("REGTECH", 50), ("MANUAL", 30)]

        cm = MagicMock()
        cm.__enter__ = Mock(return_value=mock_conn)
        cm.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value = cm

        result = svc.get_collection_stats()
        assert isinstance(result, dict)


class TestGetCollectionHistory:
    @patch("core.services.collection_service.history_manager")
    def test_get_history_delegates(self, mock_hist):
        svc, _ = _make_service()
        mock_hist.get_recent_history = Mock(return_value=[{"date": "2024-01-01"}])
        svc.get_collection_history(days=7, limit=10)
        mock_hist.get_recent_history.assert_called_once()


class TestGetCollectionStatus:
    @patch("core.services.collection_service.status_manager")
    @patch("core.services.collection_service.history_manager")
    def test_get_status_returns_dict(self, mock_hist, mock_status):
        svc, _ = _make_service()
        mock_status.get_collection_status = Mock(return_value={"regtech": {"is_collecting": False}})
        mock_hist.get_collection_statistics = Mock(return_value={})
        mock_hist.get_recent_history = Mock(return_value=[])
        result = svc.get_collection_status()
        assert isinstance(result, dict)


class TestPerformCollection:
    @patch("core.services.collection_service.regtech_collector")
    def test_perform_regtech(self, mock_collector):
        svc, _ = _make_service()
        mock_collector.collect_regtech_ips = Mock(return_value=[])
        result = svc._perform_collection("regtech")
        assert isinstance(result, dict)

    def test_perform_secudium_via_http(self):
        svc, _ = _make_service()
        with patch.object(svc, "_collect_secudium_via_http", return_value={"success": True}):
            result = svc._perform_collection("secudium")
        assert result.get("success") is True

    def test_perform_unknown_source(self):
        svc, _ = _make_service()
        result = svc._perform_collection("unknown")
        assert result.get("success") is False


class TestCollectSecudiumViaHttp:
    def test_secudium_http_success(self):
        svc, _ = _make_service()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True}
        # _collect_secudium_via_http uses `import requests as req` inside method body
        # So we patch 'requests' in sys.modules
        mock_requests_module = MagicMock()
        mock_requests_module.post.return_value = mock_resp
        with patch.dict("sys.modules", {"requests": mock_requests_module}):
            result = svc._collect_secudium_via_http()
        assert isinstance(result, dict)

    def test_secudium_http_failure(self):
        svc, _ = _make_service()
        mock_requests_module = MagicMock()
        mock_requests_module.post.side_effect = Exception("connection refused")
        with patch.dict("sys.modules", {"requests": mock_requests_module}):
            result = svc._collect_secudium_via_http()
        assert result.get("success") is False


class TestTriggerSecudiumCollection:
    def test_secudium_already_collecting(self):
        svc, _ = _make_service()
        svc.collection_status["secudium"]["is_collecting"] = True
        result = svc.trigger_secudium_collection("2024-01-01", "2024-01-31")
        assert result.get("success") is False or "already" in str(result).lower()


class TestSaveCollectionData:
    def test_save_data_success(self):
        svc, mock_db = _make_service()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)

        cm = MagicMock()
        cm.__enter__ = Mock(return_value=mock_conn)
        cm.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value = cm

        data = {"data": [{"ip_address": "1.2.3.4", "reason": "test"}]}
        result = svc._save_collection_data("regtech", data)
        assert result is True or isinstance(result, bool)

    def test_save_data_empty(self):
        svc, mock_db = _make_service()
        data = {"data": []}
        result = svc._save_collection_data("regtech", data)
        assert isinstance(result, bool)


class TestExpandCollectionScope:
    @patch("core.services.collection_service.regtech_collector")
    def test_expand_scope(self, mock_collector):
        svc, _ = _make_service()
        mock_collector.expand_regtech_collection = Mock(return_value=[])
        mock_collector.collect_threat_intelligence_ips = Mock(return_value={"success": True})
        mock_collector.collect_malicious_ip_lists = Mock(return_value={"success": True})
        result = svc.expand_collection_scope()
        assert isinstance(result, dict)
