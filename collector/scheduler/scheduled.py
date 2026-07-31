from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from .dependencies import db_service, regtech_collector
from .operation_support import REGTECH_PAGE_SIZE, SchedulerProtocol, execution_time_ms, save_blacklist_ips

logger = logging.getLogger(f"{__package__}.operations")


def run_adaptive_collection(
    scheduler: SchedulerProtocol,
    database: Any = db_service,
    collector: Any = regtech_collector,
) -> bool:
    try:
        start_time = datetime.now()
        scheduler.collection_stats["total_runs"] += 1
        scheduler.collection_stats["last_run"] = start_time.isoformat()
        logger.info("📊 적응형 수집 시작 (간격: %s초)", scheduler.collection_stats["adaptive_interval"])
        today = datetime.now()
        start_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        logger.info("📅 스케줄 수집 범위: %s ~ %s (1일)", start_date, end_date)
        collected_ips = collector.collect_blacklist_data(
            page_size=REGTECH_PAGE_SIZE, start_date=start_date, end_date=end_date, max_pages=1
        )
        if collected_ips:
            saved_count, new_count, updated_count = save_blacklist_ips(collected_ips, database)
            database.record_collection_history(
                source="REGTECH",
                success=True,
                items_collected=saved_count,
                execution_time_ms=execution_time_ms(start_time),
                new_count=new_count,
                updated_count=updated_count,
            )
            scheduler.collection_stats["successful_runs"] += 1
            scheduler.collection_stats["last_success"] = start_time.isoformat()
            scheduler.collection_stats["consecutive_failures"] = 0
            scheduler._adjust_interval_success()
            logger.info("✅ 적응형 수집 성공: 신규 %s개, 중복 %s개", new_count, updated_count)
            return True
        scheduler.collection_stats["failed_runs"] += 1
        scheduler.collection_stats["last_failure"] = start_time.isoformat()
        scheduler.collection_stats["consecutive_failures"] += 1
        scheduler._adjust_interval_failure()
        logger.warning(
            "⚠️ 적응형 수집 실패: 데이터 없음 (연속 실패: %s회)", scheduler.collection_stats["consecutive_failures"]
        )
        return False
    except Exception as exc:
        scheduler.collection_stats["failed_runs"] += 1
        scheduler.collection_stats["consecutive_failures"] += 1
        scheduler.collection_stats["last_failure"] = datetime.now().isoformat()
        scheduler._adjust_interval_failure()
        logger.error("❌ 적응형 수집 오류: %s", exc)
        return False


def run_daily_collection(schedule_name: str, database: Any = db_service, collector: Any = regtech_collector) -> None:
    logger.info("📆 일일 수집 시작: %s", schedule_name)
    credentials = database.get_collection_credentials("REGTECH")
    if not credentials:
        logger.error("❌ REGTECH 인증정보를 사용할 수 없어 일일 수집 중단")
        return
    if not credentials.get("enabled", False):
        logger.info("⏭️ REGTECH 수집 비활성화 — 건너뜀")
        return
    start_time = datetime.now()
    try:
        collected_ips = collector.collect_blacklist_data(
            start_date=None, end_date=None, page_size=REGTECH_PAGE_SIZE, max_pages=1
        )
        if collected_ips:
            saved_count, new_count, updated_count = save_blacklist_ips(collected_ips, database)
            database.record_collection_history(
                source="REGTECH",
                success=True,
                items_collected=saved_count,
                execution_time_ms=execution_time_ms(start_time),
                new_count=new_count,
                updated_count=updated_count,
            )
            logger.info("✅ 일일 수집 완료: 신규 %s개, 중복 %s개", new_count, updated_count)
            return
        logger.warning("⚠️ 일일 수집 실패: 데이터 없음")
    except Exception as exc:
        logger.error("❌ 일일 수집 오류: %s", exc)
        database.record_collection_history(
            source="REGTECH",
            success=False,
            items_collected=0,
            execution_time_ms=execution_time_ms(start_time),
            error_message=str(exc),
        )


def run_collection(scheduler: SchedulerProtocol, database: Any = db_service) -> None:
    start_time = datetime.now()
    try:
        logger.info("📊 Starting scheduled collection")
        scheduler.collection_stats["total_runs"] += 1
        scheduler.collection_stats["last_run"] = start_time
        credentials = database.get_collection_credentials("REGTECH")
        if not credentials:
            logger.error("❌ No REGTECH credentials found in database")
            logger.error("   Please save credentials via: POST /regtech/credentials")
            scheduler._record_failure("No credentials in database")
            return
        if not credentials.get("enabled", False):
            logger.info("⏭️ REGTECH 수집 비활성화 — 건너뜀")
            return
        regtech_id = credentials.get("username", "")
        regtech_pw = credentials.get("password", "")
        if not regtech_id or not regtech_pw:
            logger.error("❌ Invalid REGTECH credentials in database")
            scheduler._record_failure("Invalid credentials")
            return
        logger.info("🔑 Using REGTECH credentials from database: %s", regtech_id)
        result = scheduler._collect_regtech_data(regtech_id, regtech_pw)
        if result["success"]:
            scheduler.collection_stats["successful_runs"] += 1
            scheduler.collection_stats["last_success"] = start_time
            logger.info("✅ Collection completed: %s IPs", result["collected_count"])
            return
        scheduler._record_failure(result.get("error", "Unknown error"))
    except Exception as exc:
        logger.error("❌ Collection error: %s", exc)
        scheduler._record_failure(str(exc))
