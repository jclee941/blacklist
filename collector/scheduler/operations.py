from __future__ import annotations

from datetime import datetime, timedelta  # noqa: F401
from typing import Any, Dict
from typing import Protocol  # noqa: F401

from .cleanup import cleanup_expired_ips as _cleanup_expired_ips
from .dependencies import db_service, regtech_collector
from .manual import collect_regtech_data as _collect_regtech_data
from .manual import run_manual_collection as _run_manual_collection
from .scheduled import run_adaptive_collection as _run_adaptive_collection
from .scheduled import run_collection as _run_collection
from .scheduled import run_daily_collection as _run_daily_collection
from .stats import load_initial_stats as _load_initial_stats
from .operation_support import SchedulerProtocol


def load_initial_stats(collection_stats: Dict[str, Any]) -> None:
    return _load_initial_stats(collection_stats, db_service)


def cleanup_expired_ips() -> None:
    return _cleanup_expired_ips(db_service)


def run_daily_collection(schedule_name: str) -> None:
    return _run_daily_collection(schedule_name, db_service, regtech_collector)


def collect_regtech_data(username: str, password: str, max_pages: int | None = 1) -> Dict[str, Any]:
    return _collect_regtech_data(username, password, max_pages, db_service, regtech_collector)


def run_manual_collection(scheduler: SchedulerProtocol) -> None:
    return _run_manual_collection(scheduler, db_service)


def run_adaptive_collection(scheduler: SchedulerProtocol) -> bool:
    return _run_adaptive_collection(scheduler, db_service, regtech_collector)


def run_collection(scheduler: SchedulerProtocol) -> None:
    return _run_collection(scheduler, db_service)
