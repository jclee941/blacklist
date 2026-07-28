import pytest

from collector.scheduler import operations


class RegtechCollectorFake:
    def __init__(self) -> None:
        self.requested_page_size: int | None = None
        self.requested_max_pages: int | None = 1

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
        _ = start_date, end_date
        self.requested_page_size = page_size
        self.requested_max_pages = max_pages
        return []


class DatabaseFake:
    def record_collection_history(self, **_kwargs: str | int | bool) -> None:
        return None


def test_collect_regtech_data_uses_portal_page_size(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = RegtechCollectorFake()
    monkeypatch.setattr(operations, "regtech_collector", collector)
    monkeypatch.setattr(operations, "db_service", DatabaseFake())

    _ = operations.collect_regtech_data("username", "password", max_pages=2)

    assert collector.requested_page_size == 50


def test_collect_regtech_data_converts_unbounded_page_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collector = RegtechCollectorFake()
    monkeypatch.setattr(operations, "regtech_collector", collector)
    monkeypatch.setattr(operations, "db_service", DatabaseFake())

    _ = operations.collect_regtech_data(
        "username",
        "password",
        max_pages=operations.UNBOUNDED_PAGES,
    )

    assert collector.requested_max_pages is None
