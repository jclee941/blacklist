"""
Collection Scheduler
수집 작업 스케줄링 및 관리
"""

import logging
import schedule
import time
import threading
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]
from typing import Dict, Any, Optional
from core.database import db_service
from core.regtech_collector import regtech_collector
from .config import CollectorConfig

logger = logging.getLogger(__name__)


class CollectionScheduler:
    """수집 스케줄러 클래스"""

    def __init__(self):
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.collection_stats = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "last_run": None,
            "last_success": None,
            "last_failure": None,
            "consecutive_failures": 0,
            "adaptive_interval": CollectorConfig.COLLECTION_INTERVAL,
        }

        # 적응형 스케줄링 설정
        self.base_interval = CollectorConfig.COLLECTION_INTERVAL
        self.max_interval = 3600  # 최대 1시간
        self.min_interval = 300  # 최소 5분
        self.failure_threshold = 3  # 연속 실패 임계값

        # 자동 수집 비활성화 플래그 (환경변수)
        self.auto_collection_disabled = os.getenv("DISABLE_AUTO_COLLECTION", "false").lower() == "true"

        # 지원하는 수집 소스 (scheduler_api에서 validation에 사용)
        self.collectors = {
            "REGTECH": "_collect_regtech_data",
            "SECUDIUM": "_collect_secudium_data",
        }

        self._active_collections: set[str] = set()

        # Load initial stats from database on init
        self._load_initial_stats()

    def _load_initial_stats(self):
        """Load last collection time and run counts from database to persist across restarts"""
        try:
            stats = db_service.get_collection_stats()
            if stats:
                # Load last collection time
                if stats.get("latest_collection"):
                    last_collection = stats["latest_collection"]
                    # Convert datetime to ISO string if needed
                    if hasattr(last_collection, "isoformat"):
                        self.collection_stats["last_run"] = last_collection.isoformat()
                        self.collection_stats["last_success"] = last_collection.isoformat()
                    else:
                        self.collection_stats["last_run"] = str(last_collection)
                        self.collection_stats["last_success"] = str(last_collection)
                    logger.info(f"📅 Loaded last collection time from DB: {self.collection_stats['last_run']}")

                # Load run counts
                if stats.get("total_collections"):
                    self.collection_stats["total_runs"] = stats["total_collections"]
                if stats.get("successful_collections"):
                    self.collection_stats["successful_runs"] = stats["successful_collections"]
                if stats.get("failed_collections"):
                    self.collection_stats["failed_runs"] = stats["failed_collections"]
                logger.info(
                    f"📊 Loaded run counts from DB: total={self.collection_stats['total_runs']}, success={self.collection_stats['successful_runs']}, failed={self.collection_stats['failed_runs']}"
                )
        except Exception as e:
            logger.warning(f"⚠️ Could not load initial stats from DB: {e}")

    def start(self):
        """적응형 스케줄러 시작"""
        if self.running:
            logger.warning("⚠️ Scheduler is already running")
            return

        # 자동 수집이 비활성화된 경우
        if self.auto_collection_disabled:
            logger.warning("⚠️ Auto-collection is DISABLED by environment variable")
            logger.info("✅ Scheduler started in MANUAL-ONLY mode")
            self.running = True
            return

        logger.info("🚀 Starting collection scheduler (24시간 간격)")

        # 24시간 수집 스케줄 추가
        self._setup_time_based_schedules()

        # 스케줄러 스레드 시작
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

        logger.info("✅ Adaptive collection scheduler started")

    def _setup_time_based_schedules(self):
        """24시간 단순 스케줄 설정"""
        # 24시간마다 1회 수집 (매일 오전 2시)
        schedule.every().day.at("02:00").do(self._daily_collection, "일일 정기")

        # Secudium 수집 (매일 오전 3시)
        schedule.every().day.at("03:00").do(self._daily_secudium_collection, "Secudium 정기")

        # 매일 자정에 만료된 IP 정리
        schedule.every().day.at("00:00").do(self._cleanup_expired_ips)

        logger.info("📅 24시간 수집 스케줄 설정 완료 (REGTECH 02:00, Secudium 03:00, 만료 정리 00:00)")

    def _run_adaptive_collection(self) -> bool:
        """적응형 수집 실행"""
        try:
            start_time = datetime.now()
            self.collection_stats["total_runs"] += 1
            self.collection_stats["last_run"] = start_time.isoformat()

            logger.info(f"📊 적응형 수집 시작 (간격: {self.collection_stats['adaptive_interval']}초)")

            # 자동 수집: 1일 범위만
            today = datetime.now()
            start_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")

            logger.info(f"📅 스케줄 수집 범위: {start_date} ~ {end_date} (1일)")

            collected_ips = regtech_collector.collect_blacklist_data(
                page_size=2000, start_date=start_date, end_date=end_date, max_pages=1
            )

            if collected_ips and len(collected_ips) > 0:
                # 데이터베이스에 저장
                save_result = db_service.save_blacklist_ips(collected_ips)
                saved_count = save_result.get("total", 0) if isinstance(save_result, dict) else save_result
                new_count = save_result.get("new_count", 0) if isinstance(save_result, dict) else 0
                updated_count = save_result.get("updated_count", 0) if isinstance(save_result, dict) else 0

                # 실행 시간 계산
                execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                # 히스토리 기록
                db_service.record_collection_history(
                    source="REGTECH",
                    success=True,
                    items_collected=saved_count,
                    execution_time_ms=execution_time_ms,
                    new_count=new_count,
                    updated_count=updated_count,
                )

                # 성공 시 통계 업데이트
                self.collection_stats["successful_runs"] += 1
                self.collection_stats["last_success"] = start_time.isoformat()
                self.collection_stats["consecutive_failures"] = 0

                # 간격 단축 (데이터가 있으면 더 자주 수집)
                self._adjust_interval_success()

                logger.info(f"✅ 적응형 수집 성공: 신규 {new_count}개, 중복 {updated_count}개")
                return True
            else:
                # 실패 시 통계 업데이트
                self.collection_stats["failed_runs"] += 1
                self.collection_stats["last_failure"] = start_time.isoformat()
                self.collection_stats["consecutive_failures"] += 1

                # 간격 연장 (데이터가 없으면 덜 자주 수집)
                self._adjust_interval_failure()

                logger.warning(
                    f"⚠️ 적응형 수집 실패: 데이터 없음 (연속 실패: {self.collection_stats['consecutive_failures']}회)"
                )
                return False

        except Exception as e:
            self.collection_stats["failed_runs"] += 1
            self.collection_stats["consecutive_failures"] += 1
            self.collection_stats["last_failure"] = datetime.now().isoformat()

            self._adjust_interval_failure()

            logger.error(f"❌ 적응형 수집 오류: {e}")
            return False

    def _adjust_interval_success(self):
        """성공 시 간격 조정"""
        # 성공하면 간격을 80%로 단축 (더 자주 수집)
        new_interval = max(self.min_interval, int(self.collection_stats["adaptive_interval"] * 0.8))

        if new_interval != self.collection_stats["adaptive_interval"]:
            self.collection_stats["adaptive_interval"] = new_interval
            logger.info(f"⏰ 수집 간격 단축: {new_interval}초 (성공으로 인한 조정)")
            self._reschedule_adaptive()

    def _adjust_interval_failure(self):
        """실패 시 간격 조정"""
        # 연속 실패가 임계값을 넘으면 간격을 150%로 연장
        if self.collection_stats["consecutive_failures"] >= self.failure_threshold:
            new_interval = min(self.max_interval, int(self.collection_stats["adaptive_interval"] * 1.5))

            if new_interval != self.collection_stats["adaptive_interval"]:
                self.collection_stats["adaptive_interval"] = new_interval
                logger.warning(f"⏰ 수집 간격 연장: {new_interval}초 (연속 실패로 인한 조정)")
                self._reschedule_adaptive()

    def _reschedule_adaptive(self):
        """적응형 스케줄 재설정"""
        # 기존 적응형 스케줄 제거
        schedule.clear("adaptive")

        # 새 간격으로 스케줄 재설정
        schedule.every(self.collection_stats["adaptive_interval"]).seconds.do(self._run_adaptive_collection).tag(
            "adaptive"
        )

    def _cleanup_expired_ips(self):
        """만료된 IP 자동 비활성화 (removal_date 기준)"""
        try:
            logger.info("🧹 만료된 IP 정리 시작")

            with db_service.get_connection() as conn:
                cursor = conn.cursor()

                # 1. removal_date가 지난 IP 비활성화
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

                # 2. 3개월(90일) 이상 지난 IP 비활성화 (removal_date 미설정 또는 이미 만료된 경우만)
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

                # 3. removal_date가 미래인데 is_active=false인 IP 재활성화
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

                # 결과 조회
                cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE is_active = true")
                active_count = cursor.fetchone()[0]
                cursor.close()

            logger.info(
                f"✅ 만료된 IP 정리 완료: 만료 {expired_count}개, 3개월+ {old_count}개 비활성화, {reactivated_count}개 재활성화 (활성 IP: {active_count:,}개)"
            )

        except Exception as e:
            logger.error(f"❌ 만료된 IP 정리 오류: {e}")

    def _daily_collection(self, schedule_name: str):
        """일일 정기 수집 (24시간마다)"""
        logger.info(f"📆 일일 수집 시작: {schedule_name}")

        credentials = db_service.get_collection_credentials("REGTECH")
        if credentials and not credentials.get("enabled", False):
            logger.info("⏭️ REGTECH 수집 비활성화 — 건너뜀")
            return

        start_time = datetime.now()

        try:
            # 페이지 1개 (2000개) 수집
            collected_ips = regtech_collector.collect_blacklist_data(
                start_date=None,
                end_date=None,
                page_size=2000,
                max_pages=1,
            )

            if collected_ips and len(collected_ips) > 0:
                # 데이터베이스에 저장
                save_result = db_service.save_blacklist_ips(collected_ips)
                saved_count = save_result.get("total", 0) if isinstance(save_result, dict) else save_result
                new_count = save_result.get("new_count", 0) if isinstance(save_result, dict) else 0
                updated_count = save_result.get("updated_count", 0) if isinstance(save_result, dict) else 0

                # 실행 시간 계산
                execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                # 히스토리 기록
                db_service.record_collection_history(
                    source="REGTECH",
                    success=True,
                    items_collected=saved_count,
                    execution_time_ms=execution_time_ms,
                    new_count=new_count,
                    updated_count=updated_count,
                )

                logger.info(f"✅ 일일 수집 완료: 신규 {new_count}개, 중복 {updated_count}개")
            else:
                logger.warning("⚠️ 일일 수집 실패: 데이터 없음")

        except Exception as e:
            logger.error(f"❌ 일일 수집 오류: {e}")
            db_service.record_collection_history(
                source="REGTECH",
                success=False,
                items_collected=0,
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error_message=str(e),
            )

    def _daily_secudium_collection(self, schedule_name: str):
        """Secudium 일일 정기 수집"""
        logger.info(f"📆 Secudium 수집 시작: {schedule_name}")

        try:
            credentials = db_service.get_collection_credentials("SECUDIUM")
            if not credentials:
                logger.warning("⚠️ Secudium 자격증명 없음 — 수집 건너뜀")
                return

            if not credentials.get("enabled", False):
                logger.info("⏭️ SECUDIUM 수집 비활성화 — 건너뜀")
                return

            username = credentials.get("username", "")
            password = credentials.get("password", "")
            if not username or not password:
                logger.warning("⚠️ Secudium 자격증명 불완전 — 수집 건너뜀")
                return

            config = credentials.get("config", {})
            otp_config = CollectorConfig.get_secudium_otp_config()
            email_address = config.get("email", "") or otp_config["email"]
            email_password = config.get("email_password", "") or otp_config["email_password"]
            imap_server = config.get("imap_server", "") or otp_config["imap_server"]

            result = self._collect_secudium_data(
                username,
                password,
                email_address=email_address,
                email_password=email_password,
                imap_server=imap_server,
            )
            if result.get("success"):
                logger.info(f"✅ Secudium 일일 수집 완료: {result.get('collected_count', 0)}개 IP")
            else:
                logger.error(f"❌ Secudium 일일 수집 실패: {result.get('error')}")

        except Exception as e:
            logger.error(f"❌ Secudium 일일 수집 오류: {e}")

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
            except Exception as e:
                logger.error(f"❌ Scheduler loop error: {e}")
                time.sleep(5)

    def _run_collection(self):
        """수집 작업 실행"""
        start_time = datetime.now()

        try:
            logger.info("📊 Starting scheduled collection")
            self.collection_stats["total_runs"] += 1
            self.collection_stats["last_run"] = start_time

            # REGTECH 인증 정보 가져오기 - 데이터베이스에서 조회 (쿠키 기반 인증)
            credentials = db_service.get_collection_credentials("REGTECH")

            if not credentials:
                logger.error("❌ No REGTECH credentials found in database")
                logger.error("   Please save credentials via: POST /regtech/credentials")
                self._record_failure("No credentials in database")
                return

            if not credentials.get("enabled", False):
                logger.info("⏭️ REGTECH 수집 비활성화 — 건너뜀")
                return

            regtech_id = credentials.get("username", "")
            regtech_pw = credentials.get("password", "")

            if not regtech_id or not regtech_pw:
                logger.error("❌ Invalid REGTECH credentials in database")
                self._record_failure("Invalid credentials")
                return

            logger.info(f"🔑 Using REGTECH credentials from database: {regtech_id}")

            # REGTECH 수집 실행
            result = self._collect_regtech_data(regtech_id, regtech_pw)

            if result["success"]:
                self.collection_stats["successful_runs"] += 1
                self.collection_stats["last_success"] = start_time
                logger.info(f"✅ Collection completed: {result['collected_count']} IPs")
            else:
                self._record_failure(result.get("error", "Unknown error"))

        except Exception as e:
            logger.error(f"❌ Collection error: {e}")
            self._record_failure(str(e))

    def _collect_regtech_data(self, username: str, password: str, max_pages: int = 1) -> Dict[str, Any]:
        """REGTECH 데이터 수집

        Args:
            username: REGTECH 사용자명
            password: REGTECH 비밀번호
            max_pages: 수집할 최대 페이지 수 (기본값 1, 수동 트리거는 50)
        """
        start_time = datetime.now()

        try:
            # 인증
            if not regtech_collector.authenticate(username, password):
                return {
                    "success": False,
                    "error": "Authentication failed",
                    "collected_count": 0,
                }

            # 날짜 범위 설정
            today = datetime.now()
            end_date = today.strftime("%Y-%m-%d")

            if max_pages == 1:
                # 자동 수집: 1일 범위
                start_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
                logger.info(f"🚀 REGTECH 스케줄 수집 (1일: {start_date} ~ {end_date})")
            else:
                # 수동 수집: 3개월 범위
                start_date = (today - relativedelta(months=3)).strftime("%Y-%m-%d")
                logger.info(f"🚀 REGTECH 수동 수집 (3개월: {start_date} ~ {end_date})")

            collected_data = regtech_collector.collect_blacklist_data(
                page_size=2000,
                start_date=start_date,
                end_date=end_date,
                max_pages=max_pages,
            )

            # 데이터베이스에 저장
            saved_count = 0
            new_count = 0
            updated_count = 0
            if collected_data:
                save_result = db_service.save_blacklist_ips(collected_data)
                saved_count = save_result.get("total", 0) if isinstance(save_result, dict) else save_result
                new_count = save_result.get("new_count", 0) if isinstance(save_result, dict) else 0
                updated_count = save_result.get("updated_count", 0) if isinstance(save_result, dict) else 0

            # 실행 시간 계산
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 히스토리 기록
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

        except Exception as e:
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # 실패 히스토리 기록
            db_service.record_collection_history(
                source="REGTECH",
                success=False,
                items_collected=0,
                execution_time_ms=execution_time_ms,
                error_message=str(e),
            )

            return {"success": False, "error": str(e), "collected_count": 0}

    def _record_failure(self, error_message: str):
        """실패 기록"""
        self.collection_stats["failed_runs"] += 1
        self.collection_stats["last_failure"] = datetime.now()
        logger.error(f"❌ Collection failed: {error_message}")

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
        except Exception as e:
            logger.debug("Failed to get next scheduled run: %s", e)

        return None

    def trigger_manual_collection(self) -> Dict[str, Any]:
        """수동 수집 트리거 (전체 수집 - 50페이지)"""
        try:
            logger.info("🔄 Manual collection triggered (전체 수집 모드)")

            # 별도 스레드에서 수집 실행
            collection_thread = threading.Thread(target=self._run_manual_collection, daemon=True)
            collection_thread.start()

            return {
                "success": True,
                "message": "Manual collection started (full collection mode)",
            }

        except Exception as e:
            logger.error(f"❌ Manual collection failed: {e}")
            return {"success": False, "error": str(e)}

    def _run_manual_collection(self):
        """수동 수집 작업 실행 (전체 수집 - 50페이지)"""
        # start_time = datetime.now()

        try:
            logger.info("📊 Starting manual full collection (50 pages)")

            # REGTECH 인증 정보 가져오기
            credentials = db_service.get_collection_credentials("REGTECH")

            if not credentials:
                logger.error("❌ No REGTECH credentials found in database")
                return

            regtech_id = credentials.get("username", "")
            regtech_pw = credentials.get("password", "")

            if not regtech_id or not regtech_pw:
                logger.error("❌ Invalid REGTECH credentials in database")
                return

            logger.info(f"🔑 Using REGTECH credentials from database: {regtech_id}")

            # REGTECH 전체 수집 실행 (50페이지)
            result = self._collect_regtech_data(regtech_id, regtech_pw, max_pages=50)

            if result["success"]:
                logger.info(f"✅ Manual full collection completed: {result['collected_count']} IPs")
            else:
                logger.error(f"❌ Manual collection failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"❌ Manual collection error: {e}")

    def force_collection(self, source: str) -> Dict[str, Any]:
        """
        Force immediate collection for a specific source.

        Args:
            source: Source name ('REGTECH' or 'SECUDIUM')

        Returns:
            Collection result dictionary
        """
        if source in self._active_collections:
            logger.warning(f"⚠️ {source} collection already in progress, skipping duplicate request")
            return {"success": False, "error": f"{source} 수집이 이미 진행 중입니다", "collected_count": 0}

        self._active_collections.add(source)

        try:
            logger.info(f"🔄 Force collection triggered for {source}")

            # Get credentials from database
            credentials = db_service.get_collection_credentials(source)

            if not credentials:
                error_msg = f"No {source} credentials found in database"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg, "collected_count": 0}

            if not credentials.get("enabled", False):
                error_msg = f"{source} 수집이 비활성화되어 있습니다"
                logger.warning(f"⏭️ {error_msg}")
                return {"success": False, "error": error_msg, "collected_count": 0}

            username = credentials.get("username", "")
            password = credentials.get("password", "")

            if not username or not password:
                error_msg = f"Invalid {source} credentials in database"
                logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg, "collected_count": 0}

            logger.info(f"🔑 Using {source} credentials from database: {username}")

            # Route to appropriate collector
            if source == "REGTECH":
                result = self._collect_regtech_data(username, password, max_pages=50)
            elif source == "SECUDIUM":
                config = credentials.get("config", {})
                otp_config = CollectorConfig.get_secudium_otp_config()
                result = self._collect_secudium_data(
                    username,
                    password,
                    email_address=config.get("email", "") or otp_config["email"],
                    email_password=config.get("email_password", "") or otp_config["email_password"],
                    imap_server=config.get("imap_server", "") or otp_config["imap_server"],
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown source: {source}",
                    "collected_count": 0,
                }

            return result

        except Exception as e:
            logger.error(f"❌ Force collection error for {source}: {e}")
            return {"success": False, "error": str(e), "collected_count": 0}
        finally:
            self._active_collections.discard(source)

    def _collect_secudium_data(
        self,
        username: str,
        password: str,
        email_address: str = "",
        email_password: str = "",
        imap_server: str = "imap.kakao.com",
    ) -> Dict[str, Any]:
        """Secudium (ISAP) Black IP 데이터 수집"""
        from core.secudium_collector import SecudiumCollector

        try:
            logger.info("🔄 Starting Secudium Black IP collection...")

            collector = SecudiumCollector(db_service=db_service)

            # 인증 (email 정보가 있으면 auto OTP 모드)
            auth_kwargs = {}
            if email_address and email_password:
                auth_kwargs = {
                    "email_address": email_address,
                    "email_password": email_password,
                    "imap_server": imap_server,
                }
                logger.info("🔑 Secudium auto OTP 인증 모드 (IMAP)")

            if not collector.authenticate(username, password, **auth_kwargs):
                return {"success": False, "error": "Secudium 인증 실패", "collected_count": 0}

            result = collector.collect_data()

            if result.get("success"):
                count = result.get("collected_count", 0)
                logger.info(f"✅ Secudium collection completed: {count} IPs collected")
            else:
                logger.error(f"❌ Secudium collection failed: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"❌ Secudium collection error: {e}")
            return {"success": False, "error": str(e), "collected_count": 0}
        finally:
            try:
                collector.close()
            except Exception as e:
                logger.debug("Failed to close collector: %s", e)


# 전역 인스턴스
scheduler = CollectionScheduler()
