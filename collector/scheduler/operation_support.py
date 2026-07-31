from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Protocol

from .dependencies import db_service

REGTECH_PAGE_SIZE = 50


class SchedulerProtocol(Protocol):
    collection_stats: Dict[str, Any]

    def _adjust_interval_success(self) -> None: ...

    def _adjust_interval_failure(self) -> None: ...

    def _record_failure(self, error_message: str) -> None: ...

    def _collect_regtech_data(
        self,
        username: str,
        password: str,
        max_pages: int | None = 1,
    ) -> Dict[str, Any]: ...


def save_blacklist_ips(collected_ips: Any, database: Any = db_service) -> tuple[int, int, int]:
    save_result = database.save_blacklist_ips(collected_ips)
    if isinstance(save_result, dict):
        return (
            save_result.get("total", 0),
            save_result.get("new_count", 0),
            save_result.get("updated_count", 0),
        )
    return save_result, 0, 0


def execution_time_ms(start_time: datetime) -> int:
    return int((datetime.now() - start_time).total_seconds() * 1000)
