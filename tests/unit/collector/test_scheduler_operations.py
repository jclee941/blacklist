import threading
from datetime import date, datetime, timedelta
from typing import Protocol

import pytest

from collector.scheduler import CollectionScheduler, manager
from collector.scheduler import operations


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


def test_run_manual_collection_requests_unbounded_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_max_pages: list[int | None] = []

    monkeypatch.setattr(operations, "db_service", CredentialsDatabaseFake())

    operations.run_manual_collection(SchedulerFake(requested_max_pages))

    assert requested_max_pages == [None]


def test_force_collection_requests_unbounded_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_max_pages: list[int | None] = []
    monkeypatch.setattr(manager, "db_service", CredentialsDatabaseFake())
    scheduler = CollectionScheduler()
    monkeypatch.setattr(scheduler, "_collect_regtech_data", SchedulerFake(requested_max_pages)._collect_regtech_data)

    result = scheduler.force_collection("REGTECH")

    assert result["success"] is True
    assert requested_max_pages == [None]


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
