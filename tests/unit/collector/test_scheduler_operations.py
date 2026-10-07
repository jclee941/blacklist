import threading
from datetime import date, datetime, timedelta
from typing import Protocol

import pytest

from collector.scheduler import CollectionScheduler, manager
from collector.scheduler import manual, operations, scheduled


class RegtechCollectorFake:
    def __init__(self) -> None:
        self.requested_page_size: int | None = None
        self.requested_start_date: str | None = None
        self.requested_end_date: str | None = None
        self.requested_max_pages: int | None = None

    def authenticate(self, username: str, password: str) -> bool:
        _ = username, password
        return True

    def collect_blacklist_data(
        self,
        *,
        page_size: int,
        start_date: str,
        end_date: str,
        max_pages: int | None,
    ) -> list[dict[str, str]]:
        self.requested_page_size = page_size
        self.requested_start_date = start_date
        self.requested_end_date = end_date
        self.requested_max_pages = max_pages
        return []


class DatabaseFake:
    def record_collection_history(self, **_kwargs: str | int | bool) -> None:
        return None


class SavingDatabaseFake(DatabaseFake):
    def __init__(self) -> None:
        self.saved_ips: list[dict[str, str]] = []
        self.history: list[dict[str, str | int | bool]] = []

    def save_blacklist_ips(self, collected_ips: list[dict[str, str]]) -> dict[str, int]:
        self.saved_ips = collected_ips
        return {"total": len(collected_ips), "new_count": len(collected_ips), "updated_count": 0}

    def record_collection_history(self, **kwargs: str | int | bool) -> None:
        self.history.append(kwargs)


class MissingCredentialsDatabaseFake(DatabaseFake):
    def get_collection_credentials(self, _service_name: str) -> None:
        return None


class CredentialsDatabaseFake(DatabaseFake):
    def get_collection_stats(self) -> None:
        return None

    def get_collection_credentials(self, _service_name: str) -> dict[str, str | bool]:
        return {"username": "username", "password": "password", "enabled": True}


class SchedulerFake:
    collection_stats: dict[str, int] = {}

    def __init__(self, requested_max_pages: list[int | None]) -> None:
        self.requested_max_pages = requested_max_pages

    def _adjust_interval_success(self) -> None:
        return None

    def _adjust_interval_failure(self) -> None:
        return None

    def _record_failure(self, error_message: str) -> None:
        _ = error_message
        return None

    def _collect_regtech_data(
        self,
        username: str,
        password: str,
        max_pages: int | None = 1,
    ) -> dict[str, bool | int]:
        _ = username, password
        self.requested_max_pages.append(max_pages)
        return {"success": True, "collected_count": 0}


class AdaptiveSchedulerFake:
    def __init__(self) -> None:
        self.collection_stats: dict[str, int | None] = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "last_run": None,
            "last_success": None,
            "last_failure": None,
            "consecutive_failures": 0,
            "adaptive_interval": 600,
        }
        self.success_adjustments: int = 0
        self.failure_adjustments: int = 0

    def _adjust_interval_success(self) -> None:
        self.success_adjustments += 1

    def _adjust_interval_failure(self) -> None:
        self.failure_adjustments += 1

    def _record_failure(self, error_message: str) -> None:
        _ = error_message
        return None

    def _collect_regtech_data(
        self,
        username: str,
        password: str,
        max_pages: int | None = 1,
    ) -> dict[str, bool | int]:
        _ = username, password, max_pages
        return {"success": True, "collected_count": 0}


class CollectingRegtechCollectorFake(RegtechCollectorFake):
    def collect_blacklist_data(
        self,
        *,
        page_size: int,
        start_date: str,
        end_date: str,
        max_pages: int | None,
    ) -> list[dict[str, str]]:
        _ = super().collect_blacklist_data(
            page_size=page_size, start_date=start_date, end_date=end_date, max_pages=max_pages
        )
        return [{"ip": "192.0.2.1"}]


class ScheduledSchedulerFake(AdaptiveSchedulerFake):
    def __init__(self, requested_max_pages: list[int | None]) -> None:
        super().__init__()
        self.requested_max_pages: list[int | None] = requested_max_pages

    def _collect_regtech_data(
        self,
        username: str,
        password: str,
        max_pages: int | None = 1,
    ) -> dict[str, bool | int]:
        _ = username, password
        self.requested_max_pages.append(max_pages)
        return {"success": True, "collected_count": 0}


def test_collect_regtech_data_uses_portal_page_size(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = RegtechCollectorFake()
    monkeypatch.setattr(operations, "regtech_collector", collector)
    monkeypatch.setattr(operations, "db_service", DatabaseFake())

    _ = operations.collect_regtech_data("username", "password", max_pages=2)

    assert collector.requested_page_size == 50


def test_collect_regtech_data_uses_exact_90_day_unbounded_window(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = RegtechCollectorFake()
    monkeypatch.setattr(operations, "regtech_collector", collector)
    monkeypatch.setattr(operations, "db_service", DatabaseFake())

    _ = operations.collect_regtech_data("username", "password", max_pages=None)

    assert collector.requested_start_date is not None
    assert collector.requested_end_date is not None
    assert (
        date.fromisoformat(collector.requested_end_date) - date.fromisoformat(collector.requested_start_date)
    ).days == 90
    assert collector.requested_max_pages is None


def test_run_adaptive_collection_uses_facade_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    database = SavingDatabaseFake()
    collector = CollectingRegtechCollectorFake()
    scheduler = AdaptiveSchedulerFake()
    monkeypatch.setattr(operations, "db_service", database)
    monkeypatch.setattr(operations, "regtech_collector", collector)

    assert operations.run_adaptive_collection(scheduler) is True

    assert database.saved_ips == [{"ip": "192.0.2.1"}]
    assert database.history[0]["items_collected"] == 1
    assert scheduler.success_adjustments == 1


def test_run_collection_uses_facade_database(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_max_pages: list[int | None] = []
    database = CredentialsDatabaseFake()
    monkeypatch.setattr(operations, "db_service", database)

    operations.run_collection(ScheduledSchedulerFake(requested_max_pages))

    assert requested_max_pages == [1]


def test_operations_preserves_legacy_type_exports() -> None:
    assert operations.datetime is datetime
    assert operations.timedelta is timedelta
    assert operations.Protocol is Protocol

    exported: dict[str, object] = {}
    exec("from collector.scheduler.operations import *", exported)
    assert exported["datetime"] is datetime
    assert exported["timedelta"] is timedelta
    assert exported["Protocol"] is Protocol


def test_run_manual_collection_applies_configured_page_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_max_pages: list[int | None] = []

    monkeypatch.setattr(operations, "db_service", CredentialsDatabaseFake())

    operations.run_manual_collection(SchedulerFake(requested_max_pages))

    assert requested_max_pages == [20]


def test_force_collection_applies_configured_page_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_max_pages: list[int | None] = []
    monkeypatch.setattr(manager, "db_service", CredentialsDatabaseFake())
    scheduler = CollectionScheduler()
    monkeypatch.setattr(scheduler, "_collect_regtech_data", SchedulerFake(requested_max_pages)._collect_regtech_data)

    result = scheduler.force_collection("REGTECH")

    assert result["success"] is True
    assert requested_max_pages == [20]


def test_force_collection_admission_is_atomic(monkeypatch: pytest.MonkeyPatch) -> None:
    class CoordinatedSet(set[str]):
        def __init__(self) -> None:
            super().__init__()
            self.membership_barrier = threading.Barrier(2)

        def __contains__(self, source: object) -> bool:
            present = super().__contains__(source)
            try:
                self.membership_barrier.wait(timeout=0.1)
            except threading.BrokenBarrierError:
                pass
            return present

    monkeypatch.setattr(manager, "db_service", CredentialsDatabaseFake())
    scheduler = CollectionScheduler()
    scheduler._active_collections = CoordinatedSet()
    collection_started = threading.Event()
    release_collection = threading.Event()
    result_ready = threading.Event()
    collection_calls: list[int] = []
    results: list[dict[str, bool | int | str]] = []

    def collect(_username: str, _password: str, max_pages: int | None = 1) -> dict[str, bool | int]:
        _ = max_pages
        collection_calls.append(1)
        collection_started.set()
        assert release_collection.wait(timeout=1)
        return {"success": True, "collected_count": 0}

    def force() -> None:
        results.append(scheduler.force_collection("REGTECH"))
        result_ready.set()

    monkeypatch.setattr(scheduler, "_collect_regtech_data", collect)
    threads = [threading.Thread(target=force), threading.Thread(target=force)]
    for thread in threads:
        thread.start()

    assert collection_started.wait(timeout=1)
    duplicate_returned_before_collection_finished = result_ready.wait(timeout=0.5)
    release_collection.set()
    for thread in threads:
        thread.join(timeout=1)

    assert duplicate_returned_before_collection_finished is True
    assert len(collection_calls) == 1
    assert sum(result["success"] is True for result in results) == 1
    assert sum(result["success"] is False for result in results) == 1


def test_daily_collection_stops_when_credentials_are_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = RegtechCollectorFake()
    monkeypatch.setattr(operations, "regtech_collector", collector)
    monkeypatch.setattr(operations, "db_service", MissingCredentialsDatabaseFake())

    operations.run_daily_collection("daily")

    assert collector.requested_page_size is None


BACKFILL_TODAY = date(2026, 10, 7)


class BackfillDatabaseFake(SavingDatabaseFake):
    def __init__(self, state: dict[str, str] | None = None) -> None:
        super().__init__()
        self.state = state

    def get_initial_collection_state(self) -> dict[str, str] | None:
        return self.state

    def save_initial_collection_state(self, state: dict[str, str]) -> None:
        self.state = state


class WindowRecordingCollectorFake(RegtechCollectorFake):
    def __init__(
        self, rows: list[dict[str, str]], blocked_window: int | None = None, authenticated: bool = True
    ) -> None:
        super().__init__()
        self.rows = rows
        self.blocked_window = blocked_window
        self.authenticated = authenticated
        self.windows: list[tuple[str, str, int | None]] = []

    def authenticate(self, username: str, password: str) -> bool:
        _ = username, password
        return self.authenticated

    def collect_blacklist_data(
        self,
        *,
        page_size: int,
        start_date: str,
        end_date: str,
        max_pages: int | None,
    ) -> list[dict[str, str]]:
        _ = page_size
        self.windows.append((start_date, end_date, max_pages))
        if self.blocked_window == len(self.windows):
            raise RuntimeError("REGTECH page collection failed: blocked")
        return self.rows


def test_backfill_walks_90_days_newest_first_in_weekly_windows() -> None:
    collector = WindowRecordingCollectorFake(rows=[])
    database = BackfillDatabaseFake()

    result = manual.collect_regtech_backfill("user", "secret", database, collector, today=BACKFILL_TODAY)

    assert result["success"] is True
    assert collector.windows[0] == ("2026-10-01", "2026-10-07", None)
    assert collector.windows[-1] == ("2026-07-09", "2026-07-15", None)
    assert len(collector.windows) == 13
    for newer, older in zip(collector.windows, collector.windows[1:]):
        assert date.fromisoformat(older[1]) == date.fromisoformat(newer[0]) - timedelta(days=1)
    assert database.state is not None
    assert database.state["state"] == "complete"


def test_backfill_keeps_finished_windows_and_resumes_after_a_block() -> None:
    database = BackfillDatabaseFake()
    blocked = WindowRecordingCollectorFake(rows=[{"ip_address": "192.0.2.10"}], blocked_window=2)

    first = manual.collect_regtech_backfill("user", "secret", database, blocked, today=BACKFILL_TODAY)

    assert first["success"] is False
    assert first["collected_count"] == 1
    assert database.saved_ips == [{"ip_address": "192.0.2.10"}]
    assert database.state == {"state": "in_progress", "next_window_end": "2026-09-30"}
    assert database.history[-1]["success"] is False

    resumed = WindowRecordingCollectorFake(rows=[])
    second = manual.collect_regtech_backfill("user", "secret", database, resumed, today=BACKFILL_TODAY)

    assert second["success"] is True
    assert resumed.windows[0] == ("2026-09-24", "2026-09-30", None)


def test_backfill_stops_when_authentication_fails() -> None:
    database = BackfillDatabaseFake()
    collector = WindowRecordingCollectorFake(rows=[], authenticated=False)

    result = manual.collect_regtech_backfill("user", "secret", database, collector, today=BACKFILL_TODAY)

    assert result["success"] is False
    assert collector.windows == []
    assert database.state is None


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 7, 2, 0, 0)


def test_daily_collection_fetches_the_previous_day_without_a_page_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = RegtechCollectorFake()
    monkeypatch.setattr(operations, "regtech_collector", collector)
    monkeypatch.setattr(operations, "db_service", CredentialsDatabaseFake())
    monkeypatch.setattr(scheduled, "datetime", FrozenDatetime)

    operations.run_daily_collection("daily")

    assert (collector.requested_start_date, collector.requested_end_date) == ("2026-10-06", "2026-10-07")
    assert collector.requested_max_pages is None
