"""
Collector Configuration
수집기 관련 설정 및 환경변수 관리
"""

import json
import os
from typing import Dict, Any
import psycopg2
import logging

logger = logging.getLogger(__name__)


class CollectorConfig:
    """고성능 수집기 설정 클래스 - 최적화된 설정"""

    # 데이터베이스 설정
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "blacklist-postgres")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "blacklist")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

    # Redis 설정
    REDIS_HOST = os.getenv("REDIS_HOST", "blacklist-redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

    # REGTECH 설정 (DB-only, 환경변수는 더 이상 사용하지 않음)
    REGTECH_BASE_URL = os.getenv("REGTECH_BASE_URL", "https://regtech.fsec.or.kr")

    # SECUDIUM 설정 (DB-only, 환경변수는 더 이상 사용하지 않음)
    SECUDIUM_BASE_URL = os.getenv("SECUDIUM_BASE_URL", "https://secudium.skinfosec.co.kr")
    # Deprecated: OTP email settings are now managed via UI/DB.
    # These env vars are kept as fallback only for migration.
    _SECUDIUM_EMAIL_FALLBACK = os.getenv("SECUDIUM_EMAIL", "")
    _SECUDIUM_EMAIL_PASSWORD_FALLBACK = os.getenv("SECUDIUM_EMAIL_PASSWORD", "")
    _SECUDIUM_IMAP_SERVER_FALLBACK = os.getenv("SECUDIUM_IMAP_SERVER", "imap.kakao.com")

    # 수집 원본 아카이빙 설정
    ARCHIVE_DIR = os.getenv("COLLECTOR_ARCHIVE_DIR", "/app/data/archive")
    ARCHIVE_ENABLED = os.getenv("COLLECTOR_ARCHIVE_ENABLED", "true").lower() == "true"

    # 인증정보 캐시 (DB 조회 최소화)
    # SECURITY: Credentials are decrypted from DB and cached in memory for runtime use.
    # This is necessary for performance but should be cleared on shutdown.
    # Never log or expose these values. Use secrets module for sensitive data.
    _credentials_cache: Dict[str, Dict[str, str]] = {}
    _cache_loaded = False

    @classmethod
    def _load_credentials_from_db(cls) -> None:
        """DB에서 암호화된 인증정보 조회 및 복호화"""
        if cls._cache_loaded:
            return

        try:
            conn = psycopg2.connect(
                host=cls.POSTGRES_HOST,
                port=cls.POSTGRES_PORT,
                database=cls.POSTGRES_DB,
                user=cls.POSTGRES_USER,
                password=cls.POSTGRES_PASSWORD,
            )
            cur = conn.cursor()

            # collection_credentials 테이블에서 암호화된 인증정보 조회
            cur.execute("""
                SELECT service_name, username, password, config, encrypted
                FROM collection_credentials
                WHERE username IS NOT NULL AND password IS NOT NULL
            """)

            for row in cur.fetchall():
                source = row[0]
                username = row[1]
                password = row[2]
                row_config = row[3] if row[3] else {}
                is_encrypted = row[4] if len(row) > 4 else False

                if not is_encrypted:
                    # 평문 데이터 — 그대로 사용
                    cls._credentials_cache[source] = {
                        "username": username,
                        "password": password,
                        "config": row_config,
                    }
                    logger.info(f"✅ DB 인증정보 로드 성공 (평문): {source}")
                    continue

                # 암호화된 데이터 복호화
                try:
                    from cryptography.fernet import Fernet

                    key = os.getenv("CREDENTIAL_MASTER_KEY", "").encode()
                    if not key:
                        logger.warning(f"CREDENTIAL_MASTER_KEY 미설정, {source} 복호화 건너뜀")
                        cls._credentials_cache[source] = {
                            "username": username,
                            "password": password,
                            "config": row_config,
                        }
                        continue

                    # PBKDF2로 Fernet 키 파생 (database.py와 동일한 방식)
                    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
                    from cryptography.hazmat.primitives import hashes
                    import base64

                    salt_env = os.getenv("ENCRYPTION_SALT")
                    salt = salt_env.encode() if salt_env else b"blacklist-regtech-salt-2025"
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=100000,
                    )
                    derived_key = base64.urlsafe_b64encode(kdf.derive(key))
                    f = Fernet(derived_key)

                    # password 컬럼은 base64(Fernet(JSON)) 형태
                    # base64 디코드 → Fernet 복호화 → JSON 파싱
                    decoded = base64.b64decode(password.encode())
                    decrypted_json = f.decrypt(decoded).decode()
                    credential_data = json.loads(decrypted_json)

                    cls._credentials_cache[source] = {
                        "username": credential_data.get("username", username),
                        "password": credential_data.get("password", ""),
                        "config": credential_data.get("config", row_config),
                    }
                    logger.info(f"✅ DB 인증정보 로드 성공 (복호화): {source}")

                except Exception as decrypt_error:
                    logger.warning(f"복호화 실패 ({source}), 평문 사용: {decrypt_error}")
                    cls._credentials_cache[source] = {
                        "username": username,
                        "password": password,
                        "config": row_config,
                    }

            cur.close()
            conn.close()
            cls._cache_loaded = True
            logger.info(f"인증정보 캐시 로드 완료: {list(cls._credentials_cache.keys())}")

        except Exception as e:
            logger.warning(f"DB 인증정보 로드 실패 (환경변수 사용): {e}")

    @classmethod
    def get_regtech_credentials(cls) -> tuple:
        """
        REGTECH 인증정보 반환 (DB에서만 로드)

        Returns:
            Tuple[str, str]: (username, password)

        Raises:
            ValueError: DB에 설정된 REGTECH 인증정보가 없을 때
        """
        # DB에서 로드
        cls._load_credentials_from_db()
        creds = cls._credentials_cache.get("REGTECH", {})
        username = creds.get("username", "")
        password = creds.get("password", "")

        if not username or not password:
            logger.error("REGTECH credentials not found in database")
            raise ValueError(
                "REGTECH credentials not configured in database. Please add credentials via API: POST /api/credentials"
            )

        return (username, password)

    @classmethod
    def get_secudium_credentials(cls) -> tuple:
        """
        SECUDIUM 인증정보 반환 (DB에서만 로드)

        Returns:
            Tuple[str, str]: (username, password)

        Raises:
            ValueError: DB에 설정된 SECUDIUM 인증정보가 없을 때
        """
        cls._load_credentials_from_db()
        creds = cls._credentials_cache.get("SECUDIUM", {})
        username = creds.get("username", "")
        password = creds.get("password", "")

        if not username or not password:
            logger.error("SECUDIUM credentials not found in database")
            raise ValueError(
                "SECUDIUM credentials not configured in database. Please add credentials via API: POST /api/credentials"
            )

        return (username, password)

    @classmethod
    def get_secudium_otp_config(cls) -> Dict[str, str]:
        """
        SECUDIUM OTP 설정 반환 (DB 우선, 환경변수 fallback)

        Returns:
            Dict with keys: email, email_password, imap_server, otp_mode
        """
        cls._load_credentials_from_db()
        creds = cls._credentials_cache.get("SECUDIUM", {})
        config = creds.get("config", {})

        return {
            "email": config.get("email", "") or cls._SECUDIUM_EMAIL_FALLBACK,
            "email_password": config.get("email_password", "") or cls._SECUDIUM_EMAIL_PASSWORD_FALLBACK,
            "imap_server": config.get("imap_server", "") or cls._SECUDIUM_IMAP_SERVER_FALLBACK,
            "otp_mode": config.get("otp_mode", "manual"),
        }

    @classmethod
    def clear_credentials_cache(cls) -> None:
        """Scrub decrypted credentials from memory."""
        for source in list(cls._credentials_cache.keys()):
            creds = cls._credentials_cache[source]
            for key in list(creds.keys()):
                if isinstance(creds[key], str):
                    creds[key] = ""
                elif isinstance(creds[key], dict):
                    creds[key] = {}
        cls._credentials_cache.clear()
        cls._cache_loaded = False

    # 고성능 수집 설정
    COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", "3600"))  # 1시간
    MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "2000"))  # 배치 크기 증가

    # 성능 최적화 설정
    MAX_PAGES_PER_COLLECTION = int(os.getenv("MAX_PAGES_PER_COLLECTION", "20"))
    PAGE_SIZE = int(os.getenv("PAGE_SIZE", "2000"))  # 페이지 크기 증가
    CONNECTION_POOL_SIZE = int(os.getenv("CONNECTION_POOL_SIZE", "20"))
    MAX_MEMORY_ITEMS = int(os.getenv("MAX_MEMORY_ITEMS", "1000000"))  # 100만개로 대폭 증가

    # 캐싱 설정
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5분
    AUTH_CACHE_TTL_SECONDS = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "1800"))  # 30분
    DATA_CACHE_MAX_SIZE = int(os.getenv("DATA_CACHE_MAX_SIZE", "1000"))

    # 네트워크 최적화 설정
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0"))

    # 데이터베이스 최적화 설정
    DB_WORK_MEM = os.getenv("DB_WORK_MEM", "256MB")
    DB_MAINTENANCE_WORK_MEM = os.getenv("DB_MAINTENANCE_WORK_MEM", "256MB")
    DB_SYNCHRONOUS_COMMIT = os.getenv("DB_SYNCHRONOUS_COMMIT", "off")

    # 헬스체크 설정
    HEALTH_CHECK_PORT = int(os.getenv("HEALTH_CHECK_PORT", "8545"))

    # 로그 설정
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # 모니터링 설정
    ENABLE_PERFORMANCE_METRICS = os.getenv("ENABLE_PERFORMANCE_METRICS", "true").lower() == "true"
    METRICS_COLLECTION_INTERVAL = int(os.getenv("METRICS_COLLECTION_INTERVAL", "60"))

    @classmethod
    def get_db_connection_string(cls) -> str:
        """최적화된 데이터베이스 연결 문자열 반환"""
        return (
            f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@"
            f"{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
            f"?application_name=blacklist_collector_optimized"
        )

    @classmethod
    def get_redis_connection_params(cls) -> Dict[str, Any]:
        """최적화된 Redis 연결 파라미터 반환"""
        params = {
            "host": cls.REDIS_HOST,
            "port": cls.REDIS_PORT,
            "decode_responses": True,
            "socket_keepalive": True,
            "socket_keepalive_options": {},
            "connection_pool_max_connections": 20,
            "retry_on_timeout": True,
        }
        if cls.REDIS_PASSWORD:
            params["password"] = cls.REDIS_PASSWORD
        return params

    @classmethod
    def get_performance_config(cls) -> Dict[str, Any]:
        """성능 관련 설정 반환"""
        return {
            "batch_size": cls.BATCH_SIZE,
            "page_size": cls.PAGE_SIZE,
            "max_pages": cls.MAX_PAGES_PER_COLLECTION,
            "connection_pool_size": cls.CONNECTION_POOL_SIZE,
            "max_memory_items": cls.MAX_MEMORY_ITEMS,
            "cache_ttl": cls.CACHE_TTL_SECONDS,
            "request_timeout": cls.REQUEST_TIMEOUT,
            "max_concurrent_requests": cls.MAX_CONCURRENT_REQUESTS,
        }

    @classmethod
    def get_database_optimization_params(cls) -> Dict[str, str]:
        """데이터베이스 최적화 파라미터 반환"""
        return {
            "work_mem": cls.DB_WORK_MEM,
            "maintenance_work_mem": cls.DB_MAINTENANCE_WORK_MEM,
            "synchronous_commit": cls.DB_SYNCHRONOUS_COMMIT,
        }

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """전체 설정을 딕셔너리로 반환"""
        # REGTECH credentials 로드 (DB에서, 미설정 시 빈 값)
        try:
            regtech_id, regtech_pw = cls.get_regtech_credentials()
        except ValueError:
            regtech_id, regtech_pw = "", ""

        return {
            # 기본 설정
            "postgres_host": cls.POSTGRES_HOST,
            "postgres_port": cls.POSTGRES_PORT,
            "postgres_db": cls.POSTGRES_DB,
            "postgres_user": cls.POSTGRES_USER,
            "postgres_password": cls.POSTGRES_PASSWORD,
            "redis_host": cls.REDIS_HOST,
            "redis_port": cls.REDIS_PORT,
            "regtech_base_url": cls.REGTECH_BASE_URL,
            "regtech_id": regtech_id,
            "regtech_pw": regtech_pw,
            "collection_interval": cls.COLLECTION_INTERVAL,
            # 성능 설정
            "batch_size": cls.BATCH_SIZE,
            "page_size": cls.PAGE_SIZE,
            "max_pages_per_collection": cls.MAX_PAGES_PER_COLLECTION,
            "connection_pool_size": cls.CONNECTION_POOL_SIZE,
            "max_memory_items": cls.MAX_MEMORY_ITEMS,
            # 캐싱 설정
            "cache_ttl_seconds": cls.CACHE_TTL_SECONDS,
            "auth_cache_ttl_seconds": cls.AUTH_CACHE_TTL_SECONDS,
            "data_cache_max_size": cls.DATA_CACHE_MAX_SIZE,
            # 네트워크 설정
            "request_timeout": cls.REQUEST_TIMEOUT,
            "max_concurrent_requests": cls.MAX_CONCURRENT_REQUESTS,
            "retry_backoff_factor": cls.RETRY_BACKOFF_FACTOR,
            # 모니터링 설정
            "enable_performance_metrics": cls.ENABLE_PERFORMANCE_METRICS,
            "metrics_collection_interval": cls.METRICS_COLLECTION_INTERVAL,
            "log_level": cls.LOG_LEVEL,
        }

    @classmethod
    def validate_config(cls) -> bool:
        """설정 유효성 검사"""
        try:
            # 필수 설정 확인
            required_configs = [
                cls.POSTGRES_HOST,
                cls.POSTGRES_DB,
                cls.POSTGRES_USER,
                cls.POSTGRES_PASSWORD,
            ]

            if not all(required_configs):
                return False

            # 수치 설정 범위 확인
            if cls.BATCH_SIZE <= 0 or cls.BATCH_SIZE > 10000:
                return False

            if cls.PAGE_SIZE <= 0 or cls.PAGE_SIZE > 5000:
                return False

            return True

        except Exception:
            return False
