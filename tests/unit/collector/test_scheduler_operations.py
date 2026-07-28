import pytest

from collector.scheduler import operations


class RegtechCollectorFake:
    def __init__(self) -> None:
        self.requested_page_size: int | None = None

    def authenticate(self, username: str, password: str) -> bool:
        _ = username, password
        return True

    def collect_blacklist_data(
        self,
        *,
        page_size: int,
        start_date: str,
        end_date: str,
        max_pages: int,
    ) -> list[dict[str, str]]:
        _ = start_date, end_date, max_pages
        self.requested_page_size = page_size
        return []


class DatabaseFake:
    def record_collection_history(self, **_kwargs: str | int | bool) -> None:
        return None


class MissingCredentialsDatabaseFake(DatabaseFake):
    def get_collection_credentials(self, _service_name: str) -> None:
        return None


def test_collect_regtech_data_uses_portal_page_size(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = RegtechCollectorFake()
    monkeypatch.setattr(operations, "regtech_collector", collector)
    monkeypatch.setattr(operations, "db_service", DatabaseFake())

    _ = operations.collect_regtech_data("username", "password", max_pages=2)

    assert collector.requested_page_size == 50


def test_daily_collection_stops_when_credentials_are_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = RegtechCollectorFake()
    monkeypatch.setattr(operations, "regtech_collector", collector)
    monkeypatch.setattr(operations, "db_service", MissingCredentialsDatabaseFake())

    operations.run_daily_collection("daily")

    assert collector.requested_page_size is None
