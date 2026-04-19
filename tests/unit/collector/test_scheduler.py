"""Tests for CollectionScheduler pure methods from collector/scheduler.py."""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "test-key-for-unit-tests")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("DISABLE_AUTO_COLLECTION", "true")

# Mock heavy dependencies before importing scheduler
mock_db_module = MagicMock()
mock_db_module.db_service = MagicMock()
mock_db_module.db_service.get_collection_stats.return_value = {}
sys.modules.setdefault("core.regtech_collector", MagicMock())

if "core.database" not in sys.modules:
    sys.modules["core.database"] = mock_db_module

from collector.scheduler import CollectionScheduler


@pytest.fixture
def sched():
    with patch.object(CollectionScheduler, "_load_initial_stats"):
        s = CollectionScheduler()
    s.collection_stats = {
        "total_runs": 0,
        "successful_runs": 0,
        "failed_runs": 0,
        "last_run": None,
        "last_success": None,
        "last_failure": None,
        "consecutive_failures": 0,
        "adaptive_interval": 600,
    }
    s.base_interval = 600
    s.max_interval = 3600
    s.min_interval = 300
    s.failure_threshold = 3
    s.running = False
    return s


class TestAdjustIntervalSuccess:
    def test_shrinks_to_80_percent(self, sched):
        sched.collection_stats["adaptive_interval"] = 1000
        with patch.object(sched, "_reschedule_adaptive"):
            sched._adjust_interval_success()
        assert sched.collection_stats["adaptive_interval"] == 800

    def test_does_not_go_below_min(self, sched):
        sched.collection_stats["adaptive_interval"] = 350
        with patch.object(sched, "_reschedule_adaptive"):
            sched._adjust_interval_success()
        assert sched.collection_stats["adaptive_interval"] == 300

    def test_already_at_min_no_change(self, sched):
        sched.collection_stats["adaptive_interval"] = 300
        with patch.object(sched, "_reschedule_adaptive"):
            sched._adjust_interval_success()
        assert sched.collection_stats["adaptive_interval"] == 300

    def test_large_interval_reduction(self, sched):
        sched.collection_stats["adaptive_interval"] = 3600
        with patch.object(sched, "_reschedule_adaptive"):
            sched._adjust_interval_success()
        assert sched.collection_stats["adaptive_interval"] == 2880


class TestAdjustIntervalFailure:
    def test_no_change_below_threshold(self, sched):
        sched.collection_stats["consecutive_failures"] = 2
        sched.collection_stats["adaptive_interval"] = 600
        sched._adjust_interval_failure()
        assert sched.collection_stats["adaptive_interval"] == 600

    def test_grows_at_threshold(self, sched):
        sched.collection_stats["consecutive_failures"] = 3
        sched.collection_stats["adaptive_interval"] = 600
        with patch.object(sched, "_reschedule_adaptive"):
            sched._adjust_interval_failure()
        assert sched.collection_stats["adaptive_interval"] == 900

    def test_capped_at_max(self, sched):
        sched.collection_stats["consecutive_failures"] = 5
        sched.collection_stats["adaptive_interval"] = 3000
        with patch.object(sched, "_reschedule_adaptive"):
            sched._adjust_interval_failure()
        assert sched.collection_stats["adaptive_interval"] == 3600

    def test_above_threshold_still_grows(self, sched):
        sched.collection_stats["consecutive_failures"] = 10
        sched.collection_stats["adaptive_interval"] = 1000
        with patch.object(sched, "_reschedule_adaptive"):
            sched._adjust_interval_failure()
        assert sched.collection_stats["adaptive_interval"] == 1500


class TestGetStatus:
    def test_returns_required_keys(self, sched):
        status = sched.get_status()
        assert "running" in status
        assert "next_run" in status
        assert "stats" in status
        assert "config" in status

    def test_stats_is_copy(self, sched):
        status = sched.get_status()
        status["stats"]["total_runs"] = 999
        assert sched.collection_stats["total_runs"] == 0

    def test_config_contains_expected_keys(self, sched):
        status = sched.get_status()
        config = status["config"]
        assert "interval_seconds" in config
        assert "batch_size" in config
        assert "max_retries" in config

    def test_not_running_next_run_none(self, sched):
        sched.running = False
        status = sched.get_status()
        assert status["next_run"] is None

    def test_running_flag(self, sched):
        sched.running = True
        status = sched.get_status()
        assert status["running"] is True


class TestRecordFailure:
    def test_increments_failed_runs(self, sched):
        sched._record_failure("test error")
        assert sched.collection_stats["failed_runs"] == 1

    def test_sets_last_failure(self, sched):
        sched._record_failure("test error")
        assert sched.collection_stats["last_failure"] is not None
        assert isinstance(sched.collection_stats["last_failure"], datetime)

    def test_multiple_failures_increment(self, sched):
        sched._record_failure("err1")
        sched._record_failure("err2")
        sched._record_failure("err3")
        assert sched.collection_stats["failed_runs"] == 3


class TestCollectors:
    def test_supported_sources(self, sched):
        assert "REGTECH" in sched.collectors

    def test_collector_method_names(self, sched):
        assert sched.collectors["REGTECH"] == "_collect_regtech_data"
