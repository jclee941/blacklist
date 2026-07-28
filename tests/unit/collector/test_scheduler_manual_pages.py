import pytest
from typing_extensions import override

from collector.scheduler import manager
from collector.scheduler.manager import CollectionScheduler
from collector.scheduler.operations import UNBOUNDED_PAGES


class DatabaseFake:
    def get_collection_credentials(self, _source: str) -> dict[str, str | bool]:
        return {
            "username": "collector-user",
            "password": "collector-password",
            "enabled": True,
        }


class CollectionSchedulerHarness(CollectionScheduler):
    def __init__(self) -> None:
        self.requested_max_pages: int = 1
        super().__init__()

    @override
    def _load_initial_stats(self) -> None:
        return None

    @override
    def _collect_regtech_data(
        self,
        username: str,
        password: str,
        max_pages: int = 1,
    ) -> dict[str, str | int | bool]:
        _ = username, password
        self.requested_max_pages = max_pages
        return {"success": True, "collected_count": 0}


def test_force_collection_requests_all_ninety_day_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduler = CollectionSchedulerHarness()
    monkeypatch.setattr(manager, "db_service", DatabaseFake())

    result = scheduler.force_collection("REGTECH")

    assert result["success"] is True
    assert scheduler.requested_max_pages == UNBOUNDED_PAGES
