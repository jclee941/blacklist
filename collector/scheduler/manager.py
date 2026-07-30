"""Collection scheduler manager."""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

import schedule

from .dependencies import CollectorConfig, db_service
from .operations import (
    cleanup_expired_ips,
    collect_regtech_data as execute_regtech_collection,
    load_initial_stats,
    run_adaptive_collection,
    run_collection,
    run_daily_collection,
    run_manual_collection,
)


logger = logging.getLogger(__name__)


class CollectionScheduler:
    """수집 스케줄러 클래스"""

    def __init__(self):
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.collection_stats: Dict[str, Any] = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "last_run": None,
            "last_success": None,
            "last_failure": None,
            "consecutive_failures": 0,
            "adaptive_interval": CollectorConfig.COLLECTION_INTERVAL,
        }

        self.base_interval = CollectorConfig.COLLECTION_INTERVAL
        self.max_interval = 3600
        self.min_interval = 300
        self.failure_threshold = 3
        self.auto_collection_disabled = os.getenv("DISABLE_AUTO_COLLECTION", "false").lower() == "true"
        self.collectors = {
            "REGTECH": "_collect_regtech_data",
        }
        self._active_collections: set[str] = set()
        self._active_collections_lock = threading.Lock()
        self._load_initial_stats()

    def _load_initial_stats(self):
        """Load persisted collection statistics from the database."""
        load_initial_stats(self.collection_stats)

    def start(self):
        """적응형 스케줄러 시작"""
        if self.running:
            logger.warning("⚠️ Scheduler is already running")
            return

        if self.auto_collection_disabled:
            logger.warning("⚠️ Auto-collection is DISABLED by environment variable")
            logger.info("✅ Scheduler started in MANUAL-ONLY mode")
            self.running = True
            return

        logger.info("🚀 Starting collection scheduler (24시간 간격)")
        self._setup_time_based_schedules()
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("✅ Adaptive collection scheduler started")

    def _setup_time_based_schedules(self):
        """24시간 단순 스케줄 설정"""
        schedule.every().day.at("02:00").do(self._daily_collection, "일일 정기")
        schedule.every().day.at("00:00").do(self._cleanup_expired_ips)
        logger.info("📅 24시간 수집 스케줄 설정 완료 (REGTECH 02:00, 만료 정리 00:00)")

    def _run_adaptive_collection(self) -> bool:
        """적응형 수집 실행"""
        return run_adaptive_collection(self)

    def _adjust_interval_success(self):
        """성공 시 간격 조정"""
        new_interval = max(self.min_interval, int(self.collection_stats["adaptive_interval"] * 0.8))
        if new_interval != self.collection_stats["adaptive_interval"]:
            self.collection_stats["adaptive_interval"] = new_interval
            logger.info("⏰ 수집 간격 단축: %s초 (성공으로 인한 조정)", new_interval)
            self._reschedule_adaptive()

    def _adjust_interval_failure(self):
        """실패 시 간격 조정"""
        if self.collection_stats["consecutive_failures"] >= self.failure_threshold:
            new_interval = min(self.max_interval, int(self.collection_stats["adaptive_interval"] * 1.5))
            if new_interval != self.collection_stats["adaptive_interval"]:
                self.collection_stats["adaptive_interval"] = new_interval
                logger.warning("⏰ 수집 간격 연장: %s초 (연속 실패로 인한 조정)", new_interval)
                self._reschedule_adaptive()

    def _reschedule_adaptive(self):
        """적응형 스케줄 재설정"""
        schedule.clear("adaptive")
        schedule.every(self.collection_stats["adaptive_interval"]).seconds.do(self._run_adaptive_collection).tag(
            "adaptive"
        )

    def _cleanup_expired_ips(self):
        """만료된 IP 자동 비활성화 (removal_date 기준)"""
        cleanup_expired_ips()

    def _daily_collection(self, schedule_name: str):
        """일일 정기 수집 (24시간마다)"""
        run_daily_collection(schedule_name)

    def stop(self):
        """스케줄러 중지"""
        if not self.running:
            return

        logger.info("🛑 Stopping collection scheduler")
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        schedule.clear()
        logger.info("✅ Collection scheduler stopped")

    def _scheduler_loop(self):
        """스케줄러 루프"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as exc:
                logger.error("❌ Scheduler loop error: %s", exc)
                time.sleep(5)

    def _run_collection(self):
        """수집 작업 실행"""
        run_collection(self)

    def _collect_regtech_data(
        self,
        username: str,
        password: str,
        max_pages: int | None = 1,
    ) -> Dict[str, Any]:
        """REGTECH 데이터 수집"""
        return execute_regtech_collection(username, password, max_pages=max_pages)

    def _record_failure(self, error_message: str):
        """실패 기록"""
        self.collection_stats["failed_runs"] += 1
        self.collection_stats["last_failure"] = datetime.now()
        logger.error("❌ Collection failed: %s", error_message)

    def get_status(self) -> Dict[str, Any]:
        """스케줄러 상태 반환"""
        return {
            "running": self.running,
            "next_run": self._get_next_run_time(),
            "stats": self.collection_stats.copy(),
            "config": {
                "interval_seconds": CollectorConfig.COLLECTION_INTERVAL,
                "batch_size": CollectorConfig.BATCH_SIZE,
                "max_retries": CollectorConfig.MAX_RETRY_ATTEMPTS,
            },
        }

    def _get_next_run_time(self) -> Optional[str]:
        """다음 실행 시간 반환"""
        if not self.running:
            return None

        try:
            next_job = schedule.next_run()
            if next_job:
                return next_job.isoformat()
        except Exception as exc:
            logger.debug("Failed to get next scheduled run: %s", exc)
        return None

    def trigger_manual_collection(self) -> Dict[str, Any]:
        """수동 수집 트리거 (최근 90일 전체 수집)."""
        try:
            logger.info("🔄 Manual collection triggered (전체 수집 모드)")
            collection_thread = threading.Thread(target=self._run_manual_collection, daemon=True)
            collection_thread.start()
            return {"success": True, "message": "Manual collection started (full collection mode)"}
        except Exception as exc:
            logger.error("❌ Manual collection failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def _run_manual_collection(self):
        """수동 수집 작업 실행 (최근 90일 전체 수집)."""
        run_manual_collection(self)

    def force_collection(self, source: str) -> Dict[str, Any]:
        """Force immediate collection for a specific source."""
        with self._active_collections_lock:
            if source in self._active_collections:
                logger.warning("⚠️ %s collection already in progress, skipping duplicate request", source)
                return {"success": False, "error": f"{source} 수집이 이미 진행 중입니다", "collected_count": 0}
            self._active_collections.add(source)
        try:
            logger.info("🔄 Force collection triggered for %s", source)
            credentials = db_service.get_collection_credentials(source)
            if not credentials:
                error_msg = f"No {source} credentials found in database"
                logger.error("❌ %s", error_msg)
                return {"success": False, "error": error_msg, "collected_count": 0}

            if not credentials.get("enabled", False):
                error_msg = f"{source} 수집이 비활성화되어 있습니다"
                logger.warning("⏭️ %s", error_msg)
                return {"success": False, "error": error_msg, "collected_count": 0}

            username = credentials.get("username", "")
            password = credentials.get("password", "")
            if not username or not password:
                error_msg = f"Invalid {source} credentials in database"
                logger.error("❌ %s", error_msg)
                return {"success": False, "error": error_msg, "collected_count": 0}

            logger.info("🔑 Using %s credentials from database: %s", source, username)
            if source == "REGTECH":
                return self._collect_regtech_data(username, password, max_pages=None)

            return {"success": False, "error": f"Unknown source: {source}", "collected_count": 0}
        except Exception as exc:
            logger.error("❌ Force collection error for %s: %s", source, exc)
            return {"success": False, "error": str(exc), "collected_count": 0}
        finally:
            with self._active_collections_lock:
                self._active_collections.discard(source)


scheduler = CollectionScheduler()
