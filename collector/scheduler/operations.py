"""Scheduler operation helpers extracted from CollectionScheduler."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Protocol

from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]

from .dependencies import db_service, regtech_collector


logger = logging.getLogger(__name__)
REGTECH_PAGE_SIZE = 50


class SchedulerProtocol(Protocol):
    collection_stats: Dict[str, Any]

    def _adjust_interval_success(self) -> None: ...
    def _adjust_interval_failure(self) -> None: ...
    def _record_failure(self, error_message: str) -> None: ...
    def _collect_regtech_data(self, username: str, password: str, max_pages: int = 1) -> Dict[str, Any]: ...


def load_initial_stats(collection_stats: Dict[str, Any]) -> None:
    """Load last collection timestamps and counters from the database."""
    try:
        stats = db_service.get_collection_stats()
        if not stats:
            return

        if stats.get("latest_collection"):
            last_collection = stats["latest_collection"]
            if hasattr(last_collection, "isoformat"):
                last_value = last_collection.isoformat()
            else:
                last_value = str(last_collection)
            collection_stats["last_run"] = last_value
            collection_stats["last_success"] = last_value
            logger.info("📅 Loaded last collection time from DB: %s", last_value)

        if stats.get("total_collections"):
            collection_stats["total_runs"] = stats["total_collections"]
        if stats.get("successful_collections"):
            collection_stats["successful_runs"] = stats["successful_collections"]
        if stats.get("failed_collections"):
            collection_stats["failed_runs"] = stats["failed_collections"]

        logger.info(
            "📊 Loaded run counts from DB: total=%s, success=%s, failed=%s",
            collection_stats["total_runs"],
            collection_stats["successful_runs"],
            collection_stats["failed_runs"],
        )
    except Exception as exc:
        logger.warning("⚠️ Could not load initial stats from DB: %s", exc)


def run_adaptive_collection(scheduler: SchedulerProtocol) -> bool:
    """Run adaptive collection using the last 24h window."""
    try:
        start_time = datetime.now()
        scheduler.collection_stats["total_runs"] += 1
        scheduler.collection_stats["last_run"] = start_time.isoformat()

        logger.info("📊 적응형 수집 시작 (간격: %s초)", scheduler.collection_stats["adaptive_interval"])

        today = datetime.now()
        start_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        logger.info("📅 스케줄 수집 범위: %s ~ %s (1일)", start_date, end_date)

        collected_ips = regtech_collector.collect_blacklist_data(
            page_size=REGTECH_PAGE_SIZE,
            start_date=start_date,
            end_date=end_date,
            max_pages=1,
        )

        if collected_ips and len(collected_ips) > 0:
            saved_count, new_count, updated_count = _save_blacklist_ips(collected_ips)
            execution_time_ms = _execution_time_ms(start_time)
            db_service.record_collection_history(
                source="REGTECH",
                success=True,
                items_collected=saved_count,
                execution_time_ms=execution_time_ms,
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
            "⚠️ 적응형 수집 실패: 데이터 없음 (연속 실패: %s회)",
            scheduler.collection_stats["consecutive_failures"],
        )
        return False
    except Exception as exc:
        scheduler.collection_stats["failed_runs"] += 1
        scheduler.collection_stats["consecutive_failures"] += 1
        scheduler.collection_stats["last_failure"] = datetime.now().isoformat()
        scheduler._adjust_interval_failure()
        logger.error("❌ 적응형 수집 오류: %s", exc)
        return False


def cleanup_expired_ips() -> None:
    """Deactivate expired IPs and reactivate future-dated removals."""
    try:
        logger.info("🧹 만료된 IP 정리 시작")

        with db_service.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE blacklist_ips
                SET is_active = false
                WHERE is_active = true
                  AND removal_date IS NOT NULL
                  AND removal_date < CURRENT_DATE
                """
            )
            expired_count = cursor.rowcount

            cursor.execute(
                """
                UPDATE blacklist_ips
                SET is_active = false, updated_at = NOW()
                WHERE is_active = true
                  AND detection_date < CURRENT_DATE - INTERVAL '3 months'
                  AND (removal_date IS NULL OR removal_date < CURRENT_DATE)
                """
            )
            old_count = cursor.rowcount

            cursor.execute(
                """
                UPDATE blacklist_ips
                SET is_active = true, updated_at = NOW()
                WHERE is_active = false
                  AND removal_date IS NOT NULL
                  AND removal_date >= CURRENT_DATE
                """
            )
            reactivated_count = cursor.rowcount

            conn.commit()
            cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE is_active = true")
            active_count = cursor.fetchone()[0]
            cursor.close()

        logger.info(
            "✅ 만료된 IP 정리 완료: 만료 %s개, 3개월+ %s개 비활성화, %s개 재활성화 (활성 IP: %s개)",
            expired_count,
            old_count,
            reactivated_count,
            f"{active_count:,}",
        )
    except Exception as exc:
        logger.error("❌ 만료된 IP 정리 오류: %s", exc)


def run_daily_collection(schedule_name: str) -> None:
    """Run daily REGTECH collection."""
    logger.info("📆 일일 수집 시작: %s", schedule_name)

    credentials = db_service.get_collection_credentials("REGTECH")
    if credentials and not credentials.get("enabled", False):
        logger.info("⏭️ REGTECH 수집 비활성화 — 건너뜀")
        return

    start_time = datetime.now()
    try:
        collected_ips = regtech_collector.collect_blacklist_data(
            start_date=None,
            end_date=None,
            page_size=REGTECH_PAGE_SIZE,
            max_pages=1,
        )

        if collected_ips and len(collected_ips) > 0:
            saved_count, new_count, updated_count = _save_blacklist_ips(collected_ips)
            db_service.record_collection_history(
                source="REGTECH",
                success=True,
                items_collected=saved_count,
                execution_time_ms=_execution_time_ms(start_time),
                new_count=new_count,
                updated_count=updated_count,
            )
            logger.info("✅ 일일 수집 완료: 신규 %s개, 중복 %s개", new_count, updated_count)
            return

        logger.warning("⚠️ 일일 수집 실패: 데이터 없음")
    except Exception as exc:
        logger.error("❌ 일일 수집 오류: %s", exc)
        db_service.record_collection_history(
            source="REGTECH",
            success=False,
            items_collected=0,
            execution_time_ms=_execution_time_ms(start_time),
            error_message=str(exc),
        )


def run_collection(scheduler: SchedulerProtocol) -> None:
    """Run scheduled collection using stored REGTECH credentials."""
    start_time = datetime.now()
    try:
        logger.info("📊 Starting scheduled collection")
        scheduler.collection_stats["total_runs"] += 1
        scheduler.collection_stats["last_run"] = start_time

        credentials = db_service.get_collection_credentials("REGTECH")
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


def collect_regtech_data(username: str, password: str, max_pages: int = 1) -> Dict[str, Any]:
    """Authenticate, collect REGTECH data, save it, and record history."""
    start_time = datetime.now()
    try:
        if not regtech_collector.authenticate(username, password):
            return {"success": False, "error": "Authentication failed", "collected_count": 0}

        today = datetime.now()
        end_date = today.strftime("%Y-%m-%d")
        if max_pages == 1:
            start_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            logger.info("🚀 REGTECH 스케줄 수집 (1일: %s ~ %s)", start_date, end_date)
        else:
            start_date = (today - relativedelta(months=3)).strftime("%Y-%m-%d")
            logger.info("🚀 REGTECH 수동 수집 (3개월: %s ~ %s)", start_date, end_date)

        collected_data = regtech_collector.collect_blacklist_data(
            page_size=REGTECH_PAGE_SIZE,
            start_date=start_date,
            end_date=end_date,
            max_pages=max_pages,
        )

        saved_count = 0
        new_count = 0
        updated_count = 0
        if collected_data:
            saved_count, new_count, updated_count = _save_blacklist_ips(collected_data)

        execution_time_ms = _execution_time_ms(start_time)
        db_service.record_collection_history(
            source="REGTECH",
            success=True,
            items_collected=saved_count,
            execution_time_ms=execution_time_ms,
            new_count=new_count,
            updated_count=updated_count,
        )
        return {
            "success": True,
            "collected_count": saved_count,
            "new_count": new_count,
            "updated_count": updated_count,
            "execution_time_ms": execution_time_ms,
        }
    except Exception as exc:
        execution_time_ms = _execution_time_ms(start_time)
        db_service.record_collection_history(
            source="REGTECH",
            success=False,
            items_collected=0,
            execution_time_ms=execution_time_ms,
            error_message=str(exc),
        )
        return {"success": False, "error": str(exc), "collected_count": 0}


def run_manual_collection(scheduler: SchedulerProtocol) -> None:
    """Run the full manual REGTECH collection."""
    try:
        logger.info("📊 Starting manual full collection (50 pages)")
        credentials = db_service.get_collection_credentials("REGTECH")
        if not credentials:
            logger.error("❌ No REGTECH credentials found in database")
            return

        regtech_id = credentials.get("username", "")
        regtech_pw = credentials.get("password", "")
        if not regtech_id or not regtech_pw:
            logger.error("❌ Invalid REGTECH credentials in database")
            return

        logger.info("🔑 Using REGTECH credentials from database: %s", regtech_id)
        result = scheduler._collect_regtech_data(regtech_id, regtech_pw, max_pages=50)
        if result["success"]:
            logger.info("✅ Manual full collection completed: %s IPs", result["collected_count"])
            return

        logger.error("❌ Manual collection failed: %s", result.get("error", "Unknown error"))
    except Exception as exc:
        logger.error("❌ Manual collection error: %s", exc)


def _save_blacklist_ips(collected_ips: Any) -> tuple[int, int, int]:
    save_result = db_service.save_blacklist_ips(collected_ips)
    saved_count = save_result.get("total", 0) if isinstance(save_result, dict) else save_result
    new_count = save_result.get("new_count", 0) if isinstance(save_result, dict) else 0
    updated_count = save_result.get("updated_count", 0) if isinstance(save_result, dict) else 0
    return saved_count, new_count, updated_count


def _execution_time_ms(start_time: datetime) -> int:
    return int((datetime.now() - start_time).total_seconds() * 1000)
