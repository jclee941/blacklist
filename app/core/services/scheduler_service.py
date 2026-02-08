"""
자동 수집 스케줄러 서비스
실제 REGTECH/SECUDIUM 데이터를 주기적으로 수집
"""

import threading
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class CollectionScheduler:
    """자동 수집 스케줄러"""

    def __init__(self, db_service=None):
        """
        Initialize collection scheduler

        Args:
            db_service: DatabaseService instance for connection pool access
        """
        self.db_service = db_service
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.collection_interval = int(os.getenv("COLLECTION_INTERVAL", "3600"))  # 1시간
        self.last_collection = {}

    def start(self):
        """스케줄러 시작"""
        if self.running:
            logger.warning("스케줄러가 이미 실행 중입니다.")
            return False

        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="CollectionScheduler")
        self.scheduler_thread.start()
        logger.info(f"자동 수집 스케줄러 시작됨 (간격: {self.collection_interval}초)")
        return True

    def stop(self):
        """스케줄러 중지"""
        if not self.running:
            return False

        self.running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        logger.info("자동 수집 스케줄러 중지됨")
        return True

    def _scheduler_loop(self):
        """스케줄러 메인 루프"""
        logger.info("자동 수집 스케줄러 루프 시작")

        while self.running:
            try:
                # 수집 실행
                self._run_collection()

            except Exception as e:
                logger.error(f"자동 수집 중 오류: {e}")

            # 다음 수집까지 대기
            for _ in range(self.collection_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _run_collection(self):
        """실제 수집 실행"""
        try:
            from .collection_service import collection_service

            logger.info("🔄 자동 수집 시작")

            # REGTECH 수집 (독립 컨테이너 위임)
            try:
                regtech_ips = collection_service._collect_regtech_ips()
                if regtech_ips:
                    collected_count = len(regtech_ips)
                    logger.info(f"✅ REGTECH 수집 완료: {collected_count}개")
                    self.last_collection["regtech"] = datetime.now()
                else:
                    logger.warning("❌ REGTECH 수집 실패 또는 데이터 없음")
            except Exception as e:
                logger.error(f"REGTECH 수집 오류: {e}")

            # SECUDIUM 수집
            try:
                import requests as req

                collector_url = os.environ.get("COLLECTOR_URL", "http://blacklist-collector:8545")
                resp = req.post(
                    f"{collector_url}/api/scheduler/force-collection/SECUDIUM",
                    timeout=300,
                )
                secudium_result = resp.json() if resp.status_code == 200 else {}
                if secudium_result.get("success"):
                    collected_count = secudium_result.get("collected_count", 0)
                    logger.info(f"SECUDIUM 수집 완료: {collected_count}개")
                    self.last_collection["secudium"] = datetime.now()
                else:
                    logger.warning(f"SECUDIUM 수집 실패: {secudium_result.get('error', 'unknown')}")
            except Exception as e:
                logger.error(f"SECUDIUM 수집 오류: {e}")

            # 해제일 지난 IP 비활성화
            self._deactivate_expired_ips()

            # 통계 업데이트
            self._update_collection_stats()

        except Exception as e:
            logger.error(f"자동 수집 실행 중 오류: {e}")

    def _deactivate_expired_ips(self):
        """해제일이 지난 IP들을 자동으로 비활성 처리"""
        try:
            logger.info("🔄 해제일 만료 IP 비활성 처리 시작")

            if not self.db_service:
                logger.error("Database service not available")
                return

            conn = self.db_service.get_connection()
            cursor = conn.cursor()

            # 해제일이 지나고 아직 활성 상태인 IP들 찾기
            cursor.execute(
                """
                SELECT id, ip_address, removal_date, source
                FROM blacklist_ips
                WHERE is_active = true
                AND removal_date IS NOT NULL
                AND removal_date < CURRENT_DATE
            """
            )

            expired_ips = cursor.fetchall()

            if expired_ips:
                expired_count = len(expired_ips)
                logger.info(f"📋 해제일 만료 IP {expired_count}개 발견")

                # 해제일이 지난 IP들을 비활성 처리
                expired_ids = [str(ip[0]) for ip in expired_ips]
                placeholders = ",".join(["%s"] * len(expired_ids))

                cursor.execute(
                    f"""
                    UPDATE blacklist_ips
                    SET is_active = false,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                """,
                    expired_ids,
                )

                updated_count = cursor.rowcount
                conn.commit()

                # 로그 출력
                for ip_record in expired_ips:
                    ip_id, ip_address, removal_date, source = ip_record
                    logger.info(f"🚫 IP 비활성 처리: {ip_address} (해제일: {removal_date}, 소스: {source})")

                logger.info(f"✅ 해제일 만료 IP 비활성 처리 완료: {updated_count}개")

                # 비활성 처리 통계 기록
                cursor.execute(
                    """
                    INSERT INTO collection_history (
                        collection_type,
                        collected_count,
                        success,
                        additional_info
                    ) VALUES (%s, %s, %s, %s)
                """,
                    (
                        "expired_ip_deactivation",
                        updated_count,
                        True,
                        {
                            "deactivated_count": updated_count,
                            "expired_ips": [
                                {
                                    "ip": ip[1],
                                    "removal_date": str(ip[2]),
                                    "source": ip[3],
                                }
                                for ip in expired_ips
                            ],
                            "execution_time": datetime.now().isoformat(),
                        },
                    ),
                )

                conn.commit()

            else:
                logger.info("✅ 해제일 만료 IP 없음 - 모든 활성 IP가 유효함")

            cursor.close()
            self.db_service.return_connection(conn)

        except Exception as e:
            logger.error(f"❌ 해제일 만료 IP 비활성 처리 오류: {e}")
            if "conn" in locals():
                try:
                    conn.rollback()
                    self.db_service.return_connection(conn)
                except BaseException:
                    pass

    def _update_collection_stats(self):
        """수집 통계 업데이트"""
        try:
            if not self.db_service:
                return

            # 소스별 IP 개수 업데이트
            self.db_service.execute(
                """
                INSERT INTO collection_stats (timestamp, source, total_ips, last_seen)
                SELECT NOW(), 'REGTECH', COUNT(*), MAX(last_seen)
                FROM blacklist_ips WHERE data_source = 'REGTECH'
                ON CONFLICT (source) DO UPDATE SET
                    total_ips = EXCLUDED.total_ips,
                    last_seen = EXCLUDED.last_seen,
                    timestamp = EXCLUDED.timestamp
                """
            )

            # SECUDIUM 통계 업데이트
            self.db_service.query(
                """
                INSERT INTO collection_stats (timestamp, source, total_ips, last_seen)
                SELECT NOW(), 'secudium', COUNT(*), MAX(last_seen)
                FROM blacklist_ips WHERE source = 'secudium'
                ON CONFLICT (source) DO UPDATE SET
                    total_ips = EXCLUDED.total_ips,
                    last_seen = EXCLUDED.last_seen,
                    timestamp = EXCLUDED.timestamp
                """
            )

        except Exception as e:
            logger.error(f"통계 업데이트 중 오류: {e}")

    def get_status(self) -> Dict[str, Any]:
        """스케줄러 상태 반환"""
        return {
            "running": self.running,
            "collection_interval": self.collection_interval,
            "last_collection": {source: timestamp.isoformat() for source, timestamp in self.last_collection.items()},
            "thread_alive": (self.scheduler_thread.is_alive() if self.scheduler_thread else False),
            "next_collection_in_seconds": (self.collection_interval if self.running else 0),
        }

    def force_collection(self) -> Dict[str, Any]:
        """즉시 수집 실행"""
        try:
            self._run_collection()
            return {"success": True, "message": "수집이 즉시 실행되었습니다"}
        except Exception as e:
            return {"success": False, "error": str(e)}


from flask import current_app
from werkzeug.local import LocalProxy

collection_scheduler = LocalProxy(lambda: current_app.extensions["scheduler_service"])
