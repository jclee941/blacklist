"""Tests for CollectionScheduler pure methods from collector/scheduler.py."""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import schedule

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

from collector.scheduler import CollectionScheduler  # noqa: E402
import collector.scheduler.manager as scheduler_manager  # noqa: E402


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


class TestInitialCollection:
    @pytest.fixture
    def database(self, monkeypatch):
        database = MagicMock()
        database.get_initial_collection_state.return_value = None
        database.has_blacklist_data.return_value = False
        database.get_collection_credentials.return_value = {"enabled": True, "username": "user", "password": "secret"}
        monkeypatch.setattr(scheduler_manager, "db_service", database)
        return database

    def test_backfill_runs_when_nothing_was_collected(self, sched, database):
        with patch.object(
            sched, "_collect_regtech_backfill", return_value={"success": True, "collected_count": 6000}
        ) as collect:
            result = sched._initial_collection()

        collect.assert_called_once_with("user", "secret")
        assert result is schedule.CancelJob

    def test_existing_data_marks_the_backfill_skipped(self, sched, database):
        database.has_blacklist_data.return_value = True

        with patch.object(sched, "_collect_regtech_backfill") as collect:
            result = sched._initial_collection()

        assert result is schedule.CancelJob
        collect.assert_not_called()
        database.save_initial_collection_state.assert_called_once_with({"state": "skipped", "reason": "existing data"})

    @pytest.mark.parametrize("state", ["complete", "skipped"])
    def test_finished_backfill_is_not_repeated(self, sched, database, state):
        database.get_initial_collection_state.return_value = {"state": state}

        with patch.object(sched, "_collect_regtech_backfill") as collect:
            result = sched._initial_collection()

        assert result is schedule.CancelJob
        collect.assert_not_called()

    def test_interrupted_backfill_resumes_despite_its_own_saved_data(self, sched, database):
        database.get_initial_collection_state.return_value = {"state": "in_progress", "next_window_end": "2026-09-30"}
        database.has_blacklist_data.return_value = True

        with patch.object(sched, "_collect_regtech_backfill", return_value={"success": True}) as collect:
            result = sched._initial_collection()

        collect.assert_called_once_with("user", "secret")
        assert result is schedule.CancelJob

    @pytest.mark.parametrize("credentials", [None, {"enabled": False, "username": "user", "password": "secret"}])
    def test_waits_until_regtech_credentials_are_enabled(self, sched, database, credentials):
        database.get_collection_credentials.return_value = credentials

        with patch.object(sched, "_collect_regtech_backfill") as collect:
            result = sched._initial_collection()

        assert result is None
        collect.assert_not_called()

    def test_waits_while_another_regtech_collection_runs(self, sched, database):
        sched._active_collections.add("REGTECH")

        with patch.object(sched, "_collect_regtech_backfill") as collect:
            result = sched._initial_collection()

        assert result is None
        collect.assert_not_called()

    def test_failed_backfill_retries_after_an_hour(self, sched, database):
        failure = {"success": False, "error": "blocked"}
        with patch.object(sched, "_collect_regtech_backfill", return_value=failure) as collect:
            for now in (100.0, 100.0 + 3599, 100.0 + 3600):
                with patch.object(scheduler_manager.time, "monotonic", return_value=now):
                    assert sched._initial_collection() is None

        assert collect.call_count == 2

    def test_manual_force_collection_keeps_the_page_cap(self, sched, database):
        with patch.object(sched, "_collect_regtech_data", return_value={"success": True}) as collect:
            sched.force_collection("REGTECH")

        collect.assert_called_once_with(
            "user", "secret", max_pages=scheduler_manager.CollectorConfig.MAX_PAGES_PER_COLLECTION
        )

    def test_daily_schedule_registers_the_initial_backfill_check(self, sched):
        schedule.clear()
        try:
            sched._setup_time_based_schedules()
            jobs = schedule.get_jobs("initial")
        finally:
            schedule.clear()

        assert len(jobs) == 1
        assert jobs[0].interval == scheduler_manager.INITIAL_COLLECTION_CHECK_SECONDS
