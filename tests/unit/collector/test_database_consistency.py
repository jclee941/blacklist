from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing_extensions import override

from collector.core.database import DatabaseService


class CursorFake:
    def __init__(
        self,
        events: list[str],
        params: list[Sequence[object] | None],
    ) -> None:
        self.events: list[str] = events
        self.params: list[Sequence[object] | None] = params
        self.rowcount: int = 0

    def execute(self, query: str, _params: Sequence[object] | None = None) -> None:
        self.events.append("execute:" + " ".join(query.split()))
        self.params.append(_params)

    def executemany(self, query: str, values: list[tuple[object, ...]]) -> None:
        self.events.append("executemany:" + " ".join(query.split()))
        self.rowcount = len(values)

    def fetchall(self) -> list[tuple[str]]:
        return []

    def close(self) -> None:
        self.events.append("cursor.close")


class ConnectionFake:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.params: list[Sequence[object] | None] = []

    def cursor(self) -> CursorFake:
        return CursorFake(self.events, self.params)

    def commit(self) -> None:
        self.events.append("commit")


class DatabaseServiceHarness(DatabaseService):
    def __init__(self) -> None:
        super().__init__()
        self.connection: ConnectionFake = ConnectionFake()

    @override
    @contextmanager
    def get_connection(self) -> Iterator[ConnectionFake]:
        yield self.connection


def test_save_blacklist_ips_refreshes_snapshot_before_commit() -> None:
    service = DatabaseServiceHarness()

    result = service.save_blacklist_ips([{"ip_address": "8.8.8.8", "source": "REGTECH", "data_source": "REGTECH"}])

    snapshot_event = next(event for event in service.connection.events if "INSERT INTO collection_stats" in event)
    assert result == {"total": 1, "new_count": 1, "updated_count": 0}
    assert service.connection.events.index(snapshot_event) < service.connection.events.index("commit")


def test_record_collection_history_updates_success_status_before_commit() -> None:
    service = DatabaseServiceHarness()

    service.record_collection_history(
        source="REGTECH",
        success=True,
        items_collected=10,
        execution_time_ms=250,
        new_count=3,
        updated_count=7,
    )

    status_index = next(
        index for index, event in enumerate(service.connection.events) if "INSERT INTO collection_status" in event
    )
    assert service.connection.params[status_index] == ("REGTECH", "idle", 0, 1)
    assert status_index < service.connection.events.index("commit")
