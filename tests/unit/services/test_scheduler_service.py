"""CollectionScheduler 유닛 테스트"""

import pytest
from unittest.mock import Mock, patch

from app.core.services.scheduler_service import CollectionScheduler


@pytest.mark.unit
class TestSchedulerInit:
    """초기화 테스트"""

    def test_default_state(self):
        scheduler = CollectionScheduler()
        assert scheduler.running is False
        assert scheduler.scheduler_thread is None
        assert scheduler.last_collection == {}

    def test_default_interval(self):
        scheduler = CollectionScheduler()
        assert scheduler.collection_interval == 3600

    @patch.dict("os.environ", {"COLLECTION_INTERVAL": "1800"})
    def test_custom_interval_from_env(self):
        scheduler = CollectionScheduler()
        assert scheduler.collection_interval == 1800

    def test_db_service_stored(self):
        mock_db = Mock()
        scheduler = CollectionScheduler(db_service=mock_db)
        assert scheduler.db_service is mock_db


@pytest.mark.unit
class TestSchedulerStartStop:
    """start/stop 메서드 테스트"""

    def setup_method(self):
        self.scheduler = CollectionScheduler(db_service=Mock())

    def test_start_sets_running(self):
        with patch.object(self.scheduler, "_scheduler_loop"):
            result = self.scheduler.start()
            assert result is True
            assert self.scheduler.running is True
            assert self.scheduler.scheduler_thread is not None
            # 정리
            self.scheduler.running = False
            if self.scheduler.scheduler_thread:
                self.scheduler.scheduler_thread.join(timeout=1)

    def test_start_when_already_running(self):
        self.scheduler.running = True
        result = self.scheduler.start()
        assert result is False

    def test_stop_when_not_running(self):
        result = self.scheduler.stop()
        assert result is False

    def test_stop_sets_not_running(self):
        self.scheduler.running = True
        self.scheduler.scheduler_thread = Mock()
        self.scheduler.scheduler_thread.is_alive.return_value = False

        result = self.scheduler.stop()

        assert result is True
        assert self.scheduler.running is False

    def test_stop_joins_thread(self):
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        self.scheduler.running = True
        self.scheduler.scheduler_thread = mock_thread

        self.scheduler.stop()

        mock_thread.join.assert_called_once_with(timeout=5)

    def test_thread_is_daemon(self):
        with patch.object(self.scheduler, "_scheduler_loop"):
            self.scheduler.start()
            assert self.scheduler.scheduler_thread.daemon is True
            self.scheduler.running = False
            self.scheduler.scheduler_thread.join(timeout=1)


@pytest.mark.unit
class TestGetStatus:
    """get_status 메서드 테스트"""

    def setup_method(self):
        self.scheduler = CollectionScheduler(db_service=Mock())

    def test_status_not_running(self):
        status = self.scheduler.get_status()

        assert status["running"] is False
        assert status["collection_interval"] == 3600
        assert status["last_collection"] == {}
        assert status["thread_alive"] is False
        assert status["next_collection_in_seconds"] == 0

    def test_status_running(self):
        self.scheduler.running = True
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        self.scheduler.scheduler_thread = mock_thread

        status = self.scheduler.get_status()

        assert status["running"] is True
        assert status["thread_alive"] is True
        assert status["next_collection_in_seconds"] == 3600

    def test_status_with_last_collection(self):
        from datetime import datetime

        now = datetime.now()
        self.scheduler.last_collection = {"regtech": now}

        status = self.scheduler.get_status()

        assert "regtech" in status["last_collection"]
        assert status["last_collection"]["regtech"] == now.isoformat()


@pytest.mark.unit
class TestForceCollection:
    """force_collection 메서드 테스트"""

    def setup_method(self):
        self.scheduler = CollectionScheduler(db_service=Mock())

    def test_force_collection_success(self):
        with patch.object(self.scheduler, "_run_collection"):
            result = self.scheduler.force_collection()
            assert result["success"] is True

    def test_force_collection_error(self):
        with patch.object(self.scheduler, "_run_collection", side_effect=Exception("fail")):
            result = self.scheduler.force_collection()
            assert result["success"] is False
            assert "fail" in result["error"]
