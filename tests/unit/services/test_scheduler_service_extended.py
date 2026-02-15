"""Extended tests for scheduler_service.py - covers uncovered methods."""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from datetime import datetime


class TestSchedulerServiceExtended:
    """Tests for CollectionScheduler internal methods not covered in base tests."""

    def _make_scheduler(self):
        from core.services.scheduler_service import CollectionScheduler

        svc = CollectionScheduler(db_service=Mock())
        return svc

    # ---- _scheduler_loop ----

    def test_scheduler_loop_runs_and_stops(self):
        svc = self._make_scheduler()
        call_count = 0

        def fake_run():
            nonlocal call_count
            call_count += 1
            svc.running = False

        svc._run_collection = fake_run
        svc.running = True
        svc.collection_interval = 1
        svc._scheduler_loop()
        assert call_count == 1

    def test_scheduler_loop_handles_exception(self):
        svc = self._make_scheduler()
        call_count = 0

        def fake_run():
            nonlocal call_count
            call_count += 1
            svc.running = False
            raise Exception("collection error")

        svc._run_collection = fake_run
        svc.running = True
        svc.collection_interval = 1
        svc._scheduler_loop()
        assert call_count == 1

    # ---- _run_collection ----

    def test_run_collection_regtech_success(self):
        svc = self._make_scheduler()
        svc._deactivate_expired_ips = Mock()
        svc._update_collection_stats = Mock()

        mock_collection_svc = MagicMock()
        mock_collection_svc._collect_regtech_ips.return_value = ["1.1.1.1", "2.2.2.2"]

        mock_mod = MagicMock()
        mock_mod.collection_service = mock_collection_svc

        mock_requests = MagicMock()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True}
        mock_requests.post.return_value = mock_resp

        with patch.dict(
            "sys.modules",
            {
                "core.services.collection_service": mock_mod,
                "requests": mock_requests,
            },
        ):
            svc._run_collection()
        svc._deactivate_expired_ips.assert_called_once()
        svc._update_collection_stats.assert_called_once()

    def test_run_collection_regtech_exception(self):
        svc = self._make_scheduler()
        svc._deactivate_expired_ips = Mock()
        svc._update_collection_stats = Mock()

        mock_mod = MagicMock()
        mock_mod.collection_service._collect_regtech_ips.side_effect = Exception("regtech error")

        mock_requests = MagicMock()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True}
        mock_requests.post.return_value = mock_resp

        with patch.dict(
            "sys.modules",
            {
                "core.services.collection_service": mock_mod,
                "requests": mock_requests,
            },
        ):
            svc._run_collection()

    def test_run_collection_secudium_exception(self):
        svc = self._make_scheduler()
        svc._deactivate_expired_ips = Mock()
        svc._update_collection_stats = Mock()

        mock_mod = MagicMock()
        mock_mod.collection_service._collect_regtech_ips.return_value = []

        mock_requests = MagicMock()
        mock_requests.post.side_effect = Exception("secudium error")

        with patch.dict(
            "sys.modules",
            {
                "core.services.collection_service": mock_mod,
                "requests": mock_requests,
            },
        ):
            svc._run_collection()

    # ---- _deactivate_expired_ips ----

    def test_deactivate_expired_ips_found(self):
        svc = self._make_scheduler()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [(1, "1.1.1.1"), (2, "2.2.2.2")]
        svc.db_service.get_connection.return_value = mock_conn
        svc.db_service.return_connection = Mock()
        svc._deactivate_expired_ips()
        assert mock_conn.commit.call_count >= 1

    def test_deactivate_expired_ips_none_found(self):
        svc = self._make_scheduler()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        svc.db_service.get_connection.return_value = mock_conn
        svc.db_service.return_connection = Mock()
        svc._deactivate_expired_ips()

    def test_deactivate_expired_ips_exception(self):
        svc = self._make_scheduler()
        svc.db_service.get_connection.side_effect = Exception("db error")
        svc._deactivate_expired_ips()

    def test_deactivate_expired_ips_rollback(self):
        svc = self._make_scheduler()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [(1, "1.1.1.1")]
        mock_cursor.execute.side_effect = [None, Exception("update failed")]
        svc.db_service.get_connection.return_value = mock_conn
        svc.db_service.return_connection = Mock()
        svc._deactivate_expired_ips()
        mock_conn.rollback.assert_called()

    def test_deactivate_expired_ips_no_db_service(self):
        svc = self._make_scheduler()
        svc.db_service = None
        svc._deactivate_expired_ips()

    # ---- _update_collection_stats ----

    def test_update_collection_stats_success(self):
        svc = self._make_scheduler()
        svc.db_service.execute.return_value = 1
        svc.db_service.query.return_value = [{"count": 10}]
        svc._update_collection_stats()

    def test_update_collection_stats_exception(self):
        svc = self._make_scheduler()
        svc.db_service.execute.side_effect = Exception("db error")
        svc._update_collection_stats()

    def test_update_collection_stats_no_db_service(self):
        svc = self._make_scheduler()
        svc.db_service = None
        svc._update_collection_stats()
