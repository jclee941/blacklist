from datetime import date

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
    assert (date.fromisoformat(collector.requested_end_date) - date.fromisoformat(collector.requested_start_date)).days == 90
    assert collector.requested_max_pages is None


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


def test_daily_collection_stops_when_credentials_are_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = RegtechCollectorFake()
    monkeypatch.setattr(operations, "regtech_collector", collector)
    monkeypatch.setattr(operations, "db_service", MissingCredentialsDatabaseFake())

    operations.run_daily_collection("daily")

    assert collector.requested_page_size is None
