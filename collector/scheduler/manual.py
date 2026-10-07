from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, Final

from ..config import CollectorConfig
from .dependencies import db_service, regtech_collector
from .operation_support import REGTECH_PAGE_SIZE, SchedulerProtocol, execution_time_ms, save_blacklist_ips

logger = logging.getLogger(f"{__package__}.operations")
BACKFILL_DAYS: Final = 90
BACKFILL_WINDOW_DAYS: Final = 7


def collect_regtech_data(
    username: str,
    password: str,
    max_pages: int | None = 1,
    database: Any = db_service,
    collector: Any = regtech_collector,
) -> Dict[str, Any]:
    start_time = datetime.now()
    try:
        if not collector.authenticate(username, password):
            return {"success": False, "error": "Authentication failed", "collected_count": 0}
        today = datetime.now()
        end_date = today.strftime("%Y-%m-%d")
        start_date = (today - timedelta(days=1 if max_pages == 1 else 90)).strftime("%Y-%m-%d")
        window_name = "1일" if max_pages == 1 else "90일"
        logger.info(
            "🚀 REGTECH %s 수집 (%s: %s ~ %s)",
            "스케줄" if max_pages == 1 else "수동",
            window_name,
            start_date,
            end_date,
        )
        collected_data = collector.collect_blacklist_data(
            page_size=REGTECH_PAGE_SIZE, start_date=start_date, end_date=end_date, max_pages=max_pages
        )
        saved_count, new_count, updated_count = (0, 0, 0)
        if collected_data:
            saved_count, new_count, updated_count = save_blacklist_ips(collected_data, database)
        elapsed = execution_time_ms(start_time)
        database.record_collection_history(
            source="REGTECH",
            success=True,
            items_collected=saved_count,
            execution_time_ms=elapsed,
            new_count=new_count,
            updated_count=updated_count,
        )
        return {
            "success": True,
            "collected_count": saved_count,
            "new_count": new_count,
            "updated_count": updated_count,
            "execution_time_ms": elapsed,
        }
    except Exception as exc:
        elapsed = execution_time_ms(start_time)
        database.record_collection_history(
            source="REGTECH", success=False, items_collected=0, execution_time_ms=elapsed, error_message=str(exc)
        )
        return {"success": False, "error": str(exc), "collected_count": 0}


def collect_regtech_backfill(
    username: str,
    password: str,
    database: Any = db_service,
    collector: Any = regtech_collector,
    today: date | None = None,
) -> Dict[str, Any]:
    """Collect the last 90 days newest-first in 7-day windows, saving and checkpointing each one.

    REGTECH's WAF cuts long paging runs short, so a block ends the run without losing finished
    windows, and the next run resumes at the checkpoint the database holds instead of starting over.
    """
    start_time = datetime.now()
    current_day = today or date.today()
    oldest = current_day - timedelta(days=BACKFILL_DAYS)
    collected_count = 0
    try:
        window_end = _backfill_checkpoint(database.get_initial_collection_state()) or current_day
        if not collector.authenticate(username, password):
            return {"success": False, "error": "Authentication failed", "collected_count": 0}
        database.save_initial_collection_state({"state": "in_progress", "next_window_end": window_end.isoformat()})
        while window_end >= oldest:
            window_start = max(oldest, window_end - timedelta(days=BACKFILL_WINDOW_DAYS - 1))
            window_started = datetime.now()
            logger.info("🚀 REGTECH 최초 수집 구간: %s ~ %s", window_start, window_end)
            collected_data = collector.collect_blacklist_data(
                page_size=REGTECH_PAGE_SIZE,
                start_date=window_start.isoformat(),
                end_date=window_end.isoformat(),
                max_pages=None,
            )
            saved_count, new_count, updated_count = (0, 0, 0)
            if collected_data:
                saved_count, new_count, updated_count = save_blacklist_ips(collected_data, database)
            database.record_collection_history(
                source="REGTECH",
                success=True,
                items_collected=saved_count,
                execution_time_ms=execution_time_ms(window_started),
                new_count=new_count,
                updated_count=updated_count,
            )
            collected_count += saved_count
            window_end = window_start - timedelta(days=1)
            database.save_initial_collection_state({"state": "in_progress", "next_window_end": window_end.isoformat()})
        database.save_initial_collection_state({"state": "complete", "completed_at": datetime.now().isoformat()})
        return {
            "success": True,
            "collected_count": collected_count,
            "execution_time_ms": execution_time_ms(start_time),
        }
    except Exception as exc:
        database.record_collection_history(
            source="REGTECH",
            success=False,
            items_collected=0,
            execution_time_ms=execution_time_ms(start_time),
            error_message=str(exc),
        )
        return {"success": False, "error": str(exc), "collected_count": collected_count}


def _backfill_checkpoint(state: Dict[str, Any] | None) -> date | None:
    try:
        return date.fromisoformat(str((state or {})["next_window_end"]))
    except (KeyError, ValueError):
        return None


def run_manual_collection(scheduler: SchedulerProtocol, database: Any = db_service) -> None:
    try:
        logger.info("📊 Starting bounded manual collection (last 90 days)")
        credentials = database.get_collection_credentials("REGTECH")
        if not credentials:
            logger.error("❌ No REGTECH credentials found in database")
            return
        regtech_id = credentials.get("username", "")
        regtech_pw = credentials.get("password", "")
        if not regtech_id or not regtech_pw:
            logger.error("❌ Invalid REGTECH credentials in database")
            return
        logger.info("🔑 Using REGTECH credentials from database: %s", regtech_id)
        result = scheduler._collect_regtech_data(
            regtech_id,
            regtech_pw,
            max_pages=CollectorConfig.MAX_PAGES_PER_COLLECTION,
        )
        if result["success"]:
            logger.info("✅ Manual full collection completed: %s IPs", result["collected_count"])
            return
        logger.error("❌ Manual collection failed: %s", result.get("error", "Unknown error"))
    except Exception as exc:
        logger.error("❌ Manual collection error: %s", exc)
