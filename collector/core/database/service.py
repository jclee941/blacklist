"""Database service for collector.

데이터베이스 연결 및 관리 서비스
"""

import base64
import importlib
import json
import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from psycopg2.pool import SimpleConnectionPool

try:
    from ...config import CollectorConfig
except ImportError:
    try:
        CollectorConfig = importlib.import_module("collector.config").CollectorConfig
    except ImportError:
        CollectorConfig = importlib.import_module("config").CollectorConfig

try:
    from ...exceptions import CredentialDecryptionError, MissingMasterKeyError
except ImportError:
    from exceptions import CredentialDecryptionError, MissingMasterKeyError
from .queries import DatabaseQueryMixin


logger = logging.getLogger(__package__ or __name__)


class DatabaseService(DatabaseQueryMixin):
    """고성능 데이터베이스 서비스 클래스 - 최적화된 배치 처리 및 캐싱"""

    def __init__(self):
        self.pool: Optional[SimpleConnectionPool] = None
        self._cache_max_size = 1000000
        self._batch_buffer: List[Dict[str, Any]] = []
        self._cipher_suite = None
        self._setup_decryption()
        self.ip_cache: Dict[str, float] = {}
        self.ip_cache_ttl: int = 86400
        self.ip_cache_max_size: int = 100000

    def _setup_decryption(self):
        """암호화 키 설정 (복호화용)"""
        try:
            master_key = os.getenv("CREDENTIAL_MASTER_KEY")
            if not master_key:
                logger.warning("CREDENTIAL_MASTER_KEY not set, credential decryption disabled")
                self._cipher_suite = None
                return

            salt_env = os.getenv("ENCRYPTION_SALT")
            if not salt_env:
                logger.error("ENCRYPTION_SALT is required when CREDENTIAL_MASTER_KEY is configured")
                self._cipher_suite = None
                return
            salt = salt_env.encode()

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
            self._cipher_suite = Fernet(key)

            logger.info("🔐 복호화 시스템 초기화 완료")
        except Exception as e:
            logger.error(f"❌ 복호화 시스템 초기화 실패: {e}")
            self._cipher_suite = None

    def _decrypt_password(self, encrypted_data: str, service_name: str) -> str:
        """암호화된 비밀번호 복호화"""
        if not self._cipher_suite:
            error = MissingMasterKeyError()
            logger.error("❌ %s", error)
            raise error

        try:
            decoded = base64.b64decode(encrypted_data.encode())
            decrypted = self._cipher_suite.decrypt(decoded)
            decrypted_json = decrypted.decode()
            credential_data = json.loads(decrypted_json)
            return credential_data.get("password", "")
        except Exception as e:
            logger.error(f"❌ 비밀번호 복호화 실패: {e}")
            raise CredentialDecryptionError(service_name, e) from e

    def _evict_stale_ips(self) -> int:
        """Evict stale IPs by TTL, then LRU if over max size.

        Returns:
            Number of IPs evicted.
        """
        evicted = 0
        current_time = time.time()

        stale_keys = [ip for ip, ts in self.ip_cache.items() if current_time - ts > self.ip_cache_ttl]
        for ip in stale_keys:
            del self.ip_cache[ip]
            evicted += 1

        if len(self.ip_cache) > self.ip_cache_max_size:
            sorted_ips = sorted(self.ip_cache.items(), key=lambda x: x[1])
            num_to_evict = max(
                len(self.ip_cache) - self.ip_cache_max_size + 1,
                len(self.ip_cache) // 10,
            )
            for ip, _ in sorted_ips[:num_to_evict]:
                del self.ip_cache[ip]
                evicted += 1

        if evicted > 0:
            logger.info(f"IP cache eviction: {evicted} entries removed, {len(self.ip_cache)} remaining")

        return evicted

    def _initialize_connection_pool(self):
        """연결 풀 초기화 - 고성능 설정"""
        try:
            connection_params = CollectorConfig.get_postgres_connection_params()
            connection_params.update(
                {
                    "connect_timeout": 10,
                    "application_name": "blacklist_collector_optimized",
                }
            )
            self.pool = SimpleConnectionPool(
                minconn=2,
                maxconn=20,
                **connection_params,
            )
            logger.info("✅ 고성능 데이터베이스 연결 풀 초기화 완료")
        except Exception as e:
            logger.error(f"❌ 데이터베이스 풀 초기화 실패: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """최적화된 연결 풀에서 연결 가져오기"""
        if self.pool is None:
            self._initialize_connection_pool()

        if self.pool is None:
            logger.error("❌ 데이터베이스 연결 풀이 초기화되지 않음")
            raise RuntimeError("Database connection pool is not initialized")

        conn = None
        try:
            conn = self.pool.getconn()
            if conn is None:
                raise RuntimeError("Failed to get connection from pool")
            conn.autocommit = False
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"데이터베이스 연결 오류: {e}")
            raise
        finally:
            if conn and self.pool:
                self.pool.putconn(conn)

    def test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                return result[0] == 1
        except Exception as e:
            logger.error(f"데이터베이스 연결 테스트 실패: {e}")
            return False

    def get_collection_credentials(self, service_name: str) -> Optional[Dict[str, Any]]:
        """수집 서비스 인증 정보 조회 - 암호화된 비밀번호 자동 복호화"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT service_name, username, password, encrypted,
                           enabled, collection_interval, last_collection, config
                    FROM collection_credentials
                    WHERE service_name = %s
                """,
                    (service_name,),
                )
                result = cursor.fetchone()
                cursor.close()

                if result:
                    (
                        service_name,
                        username,
                        password,
                        encrypted,
                        enabled,
                        interval,
                        last_collection,
                        config,
                    ) = result

                    final_password = password
                    if encrypted and password:
                        logger.info(f"🔐 {service_name} 암호화된 비밀번호 복호화 중...")
                        final_password = self._decrypt_password(password, service_name)

                    if isinstance(config, str):
                        try:
                            config = json.loads(config)
                        except (json.JSONDecodeError, TypeError):
                            config = {}
                    elif config is None:
                        config = {}

                    return {
                        "service_name": service_name,
                        "username": username,
                        "password": final_password,
                        "enabled": enabled,
                        "collection_interval": interval,
                        "last_collection": last_collection,
                        "config": config,
                    }

                return None
        except Exception as e:
            logger.error(f"인증 정보 조회 실패 {service_name}: {e}")
            return None

    def save_blacklist_ips(self, ip_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """최적화된 블랙리스트 IP 데이터 저장 - 대용량 배치 처리.

        Returns:
            Dict with 'total', 'new_count', 'updated_count' keys
        """
        if not ip_data:
            return {"total": 0, "new_count": 0, "updated_count": 0}

        saved_count = 0
        new_count = 0
        updated_count = 0
        processing_start = time.time()

        try:
            logger.info(f"🚀 대용량 배치 처리 시작: {len(ip_data)}개 IP")

            filtered_ips, excluded_count = self._filter_invalid_ips(ip_data)
            logger.info(f"🛡️ 오탐 필터링 완료: {excluded_count}개 제외 (사설 IP, 잘못된 형식 등)")

            if not filtered_ips:
                logger.warning("⚠️ 필터링 후 유효한 IP가 없습니다")
                return {"total": 0, "new_count": 0, "updated_count": 0}

            unique_ips = self._memory_optimized_dedup(filtered_ips)
            logger.info(f"📊 중복 제거 완료: {len(unique_ips)}개 고유 IP")

            existing_ips = self._batch_check_existing_ips([item["ip_address"] for item in unique_ips])

            new_count = len([ip for ip in unique_ips if ip["ip_address"] not in existing_ips])
            updated_count = len(existing_ips)

            logger.info(f"📊 신규: {new_count}개, 중복(업데이트): {updated_count}개")

            if not unique_ips:
                logger.info("✅ 처리할 IP가 없습니다")
                return {"total": 0, "new_count": 0, "updated_count": 0}

            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SET work_mem = '256MB'")
                cursor.execute("SET maintenance_work_mem = '256MB'")
                cursor.execute("SET synchronous_commit = off")
                cursor.execute("BEGIN")

                chunk_size = CollectorConfig.BATCH_SIZE
                total_chunks = (len(unique_ips) + chunk_size - 1) // chunk_size

                for chunk_idx, chunk in enumerate(self._get_batches(unique_ips, chunk_size)):
                    chunk_saved = self._optimized_batch_insert(cursor, chunk)
                    saved_count += chunk_saved

                    if chunk_idx % 10 == 0:
                        logger.info(f"📈 처리 진행률: {chunk_idx + 1}/{total_chunks} 청크 완료")

                cursor.execute(
                    """
                    INSERT INTO collection_stats (timestamp, source, total_ips, last_seen)
                    SELECT CURRENT_TIMESTAMP,
                           COALESCE(data_source, 'UNKNOWN'),
                           COUNT(*),
                           MAX(last_seen)
                    FROM blacklist_ips
                    GROUP BY COALESCE(data_source, 'UNKNOWN')
                    ON CONFLICT (source) DO UPDATE SET
                        timestamp = EXCLUDED.timestamp,
                        total_ips = EXCLUDED.total_ips,
                        last_seen = EXCLUDED.last_seen
                    """
                )

                conn.commit()
                cursor.close()

                processing_time = time.time() - processing_start
                logger.info(
                    f"✅ 대용량 배치 처리 완료: 신규 {new_count}개, 중복 {updated_count}개 ({processing_time:.2f}초)"
                )

        except Exception as e:
            logger.error(f"❌ 대용량 배치 처리 실패: {e}")

        return {
            "total": saved_count,
            "new_count": new_count,
            "updated_count": updated_count,
        }

    def record_collection_history(
        self,
        source: str,
        success: bool,
        items_collected: int,
        execution_time_ms: int,
        error_message: Optional[str] = None,
        new_count: int = 0,
        updated_count: int = 0,
    ):
        try:
            details = json.dumps({"new_count": new_count, "updated_count": updated_count})
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO collection_history
                    (service_name, success, items_collected, execution_time_ms,
                     error_message, collection_date, details)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                """,
                    (
                        source,
                        success,
                        items_collected,
                        execution_time_ms,
                        error_message or "",
                        details,
                    ),
                )
                status = "idle" if success else "error"
                error_increment = 0 if success else 1
                success_increment = 1 if success else 0
                cursor.execute(
                    """
                    INSERT INTO collection_status
                    (service_name, enabled, last_run, status, error_count, success_count)
                    VALUES (%s, TRUE, CURRENT_TIMESTAMP, %s, %s, %s)
                    ON CONFLICT (service_name) DO UPDATE SET
                        enabled = EXCLUDED.enabled,
                        last_run = EXCLUDED.last_run,
                        status = EXCLUDED.status,
                        error_count = collection_status.error_count + EXCLUDED.error_count,
                        success_count = collection_status.success_count + EXCLUDED.success_count
                    """,
                    (source, status, error_increment, success_increment),
                )
                conn.commit()
                cursor.close()
                logger.info(f"📊 수집 히스토리 기록: {source} (신규: {new_count}, 중복: {updated_count})")
        except Exception as e:
            logger.error(f"❌ 수집 히스토리 기록 실패: {e}")

    def get_total_ip_count(self) -> int:
        """전체 IP 개수 반환 - 최초 수집 여부 확인용"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM blacklist_ips")
                result = cursor.fetchone()
                cursor.close()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"총 IP 개수 조회 실패: {e}")
            return 0

    def get_collection_status(
        self,
        service_name: str,
    ) -> dict[str, str | int | bool | None] | None:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT service_name, enabled, last_run, status,
                           error_count, success_count
                    FROM collection_status
                    WHERE service_name = %s
                    """,
                    (service_name,),
                )
                result = cursor.fetchone()
                cursor.close()

                if not result:
                    return None

                last_run = result[2].isoformat() if result[2] else None
                return {
                    "service_name": result[0],
                    "enabled": result[1],
                    "last_run": last_run,
                    "status": result[3],
                    "error_count": result[4],
                    "success_count": result[5],
                }
        except Exception as e:
            logger.error(f"수집 상태 조회 실패 {service_name}: {e}")
            return None

    def get_collection_stats(self) -> Dict[str, Any]:
        """고성능 수집 통계 조회"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    WITH stats AS (
                        SELECT
                            COUNT(*) as total_ips,
                            COUNT(*) FILTER (WHERE is_active = true) as active_ips,
                            MAX(created_at) as latest_collection
                        FROM blacklist_ips
                    ),
                    source_stats AS (
                        SELECT json_object_agg(COALESCE(data_source, 'UNKNOWN'), cnt) as source_breakdown
                        FROM (
                            SELECT data_source, COUNT(*) as cnt
                            FROM blacklist_ips
                            GROUP BY data_source
                        ) s
                    )
                    SELECT s.total_ips, s.active_ips, s.latest_collection,
                           ss.source_breakdown
                    FROM stats s CROSS JOIN source_stats ss
                """
                )

                result = cursor.fetchone()
                cursor.close()

                if result:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT
                            COUNT(*) as total_collections,
                            COUNT(*) FILTER (WHERE success = true) as successful_collections,
                            COUNT(*) FILTER (WHERE success = false) as failed_collections
                        FROM collection_history
                        """
                    )
                    history_result = cursor.fetchone()
                    cursor.close()

                    return {
                        "total_ips": result[0],
                        "active_ips": result[1],
                        "latest_collection": result[2],
                        "source_breakdown": result[3] or {},
                        "total_collections": history_result[0] if history_result else 0,
                        "successful_collections": history_result[1] if history_result else 0,
                        "failed_collections": history_result[2] if history_result else 0,
                        "performance_mode": "optimized",
                    }

        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")

        return {}


db_service = DatabaseService()
