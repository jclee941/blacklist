from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from ..config import CollectorConfig
from .dependencies import db_service, regtech_collector
from .operation_support import REGTECH_PAGE_SIZE, SchedulerProtocol, execution_time_ms, save_blacklist_ips

logger = logging.getLogger(f"{__package__}.operations")


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
