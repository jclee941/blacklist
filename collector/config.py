import json
import os
from typing import Dict, Any
import psycopg2
import logging
from urllib.parse import quote

from .exceptions import CredentialDecryptionError, MissingMasterKeyError

logger = logging.getLogger(__name__)


class CollectorConfig:
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "blacklist-postgres")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "blacklist")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
    INTERNAL_CA_CERT = os.getenv("INTERNAL_CA_CERT", "/run/blacklist/ca.crt")

    REDIS_HOST = os.getenv("REDIS_HOST", "blacklist-redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

    # REGTECH 설정 (DB-only, 환경변수는 더 이상 사용하지 않음)
    REGTECH_BASE_URL = os.getenv("REGTECH_BASE_URL", "https://regtech.fsec.or.kr")

    ARCHIVE_DIR = os.getenv("COLLECTOR_ARCHIVE_DIR", "/app/data/archive")
    ARCHIVE_ENABLED = os.getenv("COLLECTOR_ARCHIVE_ENABLED", "true").lower() == "true"
    MAX_ARCHIVE_BYTES = int(os.getenv("COLLECTOR_MAX_ARCHIVE_BYTES", str(512 * 1024 * 1024)))
    ARCHIVE_RETENTION_DAYS = int(os.getenv("COLLECTOR_ARCHIVE_RETENTION_DAYS", "30"))
    MAX_DOWNLOAD_BYTES = int(os.getenv("COLLECTOR_MAX_DOWNLOAD_BYTES", str(10 * 1024 * 1024)))

    # 인증정보 캐시 (DB 조회 최소화)
    # SECURITY: Credentials are decrypted from DB and cached in memory for runtime use.
    # This is necessary for performance but should be cleared on shutdown.
    # Never log or expose these values. Use secrets module for sensitive data.
    _credentials_cache: Dict[str, Dict[str, Any]] = {}
    _cache_loaded = False

    @classmethod
    def _load_credentials_from_db(cls) -> None:
        if cls._cache_loaded:
            return

        try:
            conn = psycopg2.connect(
                **cls.get_postgres_connection_params(),
            )
            cur = conn.cursor()

            cur.execute("""
                SELECT service_name, username, password, config, encrypted
                FROM collector_regtech_credentials
                WHERE username IS NOT NULL AND password IS NOT NULL
            """)

            for row in cur.fetchall():
                source = row[0]
                if source != "REGTECH":
                    continue

                username = row[1]
                password = row[2]
                row_config = row[3] if row[3] else {}
                is_encrypted = row[4] if len(row) > 4 else False

                if not is_encrypted:
                    cls._credentials_cache[source] = {
                        "username": username,
                        "password": password,
                        "config": row_config,
                    }
                    logger.info(f"✅ DB 인증정보 로드 성공 (평문): {source}")
                    continue

                try:
                    from cryptography.fernet import Fernet

                    key = os.getenv("CREDENTIAL_MASTER_KEY", "").encode()
                    if not key:
                        logger.error("❌ %s", MissingMasterKeyError())
                        continue

                    # PBKDF2로 Fernet 키 파생 (database.py와 동일한 방식)
                    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
                    from cryptography.hazmat.primitives import hashes
                    import base64

                    salt_env = os.getenv("ENCRYPTION_SALT", "")
                    if not salt_env:
                        logger.error("Encrypted REGTECH credentials require ENCRYPTION_SALT")
                        continue
                    salt = salt_env.encode()
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
                    logger.error("❌ %s", CredentialDecryptionError(source, decrypt_error))

            cur.close()
            conn.close()
            cls._cache_loaded = True
            logger.info(f"인증정보 캐시 로드 완료: {list(cls._credentials_cache.keys())}")

        except Exception as e:
            logger.warning(f"DB 인증정보 로드 실패: {e}")

    @classmethod
    def get_regtech_credentials(cls) -> tuple[str, str]:
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

    COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", "3600"))
    MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "2000"))

    MAX_PAGES_PER_COLLECTION = int(os.getenv("MAX_PAGES_PER_COLLECTION", "20"))
    PAGE_SIZE = int(os.getenv("PAGE_SIZE", "2000"))
    CONNECTION_POOL_SIZE = int(os.getenv("CONNECTION_POOL_SIZE", "20"))
    MAX_MEMORY_ITEMS = int(os.getenv("MAX_MEMORY_ITEMS", "1000000"))

    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    AUTH_CACHE_TTL_SECONDS = int(os.getenv("AUTH_CACHE_TTL_SECONDS", "1800"))
    DATA_CACHE_MAX_SIZE = int(os.getenv("DATA_CACHE_MAX_SIZE", "1000"))

    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
    RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0"))

    DB_WORK_MEM = os.getenv("DB_WORK_MEM", "256MB")
    DB_MAINTENANCE_WORK_MEM = os.getenv("DB_MAINTENANCE_WORK_MEM", "256MB")
    DB_SYNCHRONOUS_COMMIT = os.getenv("DB_SYNCHRONOUS_COMMIT", "off")

    HEALTH_CHECK_PORT = int(os.getenv("HEALTH_CHECK_PORT", "8545"))

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_MAX_BYTES = int(os.getenv("COLLECTOR_LOG_MAX_BYTES", str(10 * 1024 * 1024)))
    LOG_BACKUP_COUNT = int(os.getenv("COLLECTOR_LOG_BACKUP_COUNT", "5"))

    ENABLE_PERFORMANCE_METRICS = os.getenv("ENABLE_PERFORMANCE_METRICS", "true").lower() == "true"
    METRICS_COLLECTION_INTERVAL = int(os.getenv("METRICS_COLLECTION_INTERVAL", "60"))

    @classmethod
    def get_db_connection_string(cls) -> str:
        return (
            f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@"
            f"{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
            f"?application_name=blacklist_collector_optimized&sslmode=verify-full"
            f"&sslrootcert={quote(cls.INTERNAL_CA_CERT, safe='')}"
        )

    @classmethod
    def get_postgres_connection_params(cls) -> Dict[str, Any]:
        return {
            "host": cls.POSTGRES_HOST,
            "port": cls.POSTGRES_PORT,
            "database": cls.POSTGRES_DB,
            "user": cls.POSTGRES_USER,
            "password": cls.POSTGRES_PASSWORD,
            "sslmode": "verify-full",
            "sslrootcert": cls.INTERNAL_CA_CERT,
        }

    @classmethod
    def get_redis_connection_params(cls) -> Dict[str, Any]:
        params = {
            "host": cls.REDIS_HOST,
            "port": cls.REDIS_PORT,
            "decode_responses": True,
            "socket_keepalive": True,
            "socket_keepalive_options": {},
            "max_connections": 20,
            "ssl": True,
            "ssl_ca_certs": cls.INTERNAL_CA_CERT,
            "ssl_cert_reqs": "required",
        }
        if cls.REDIS_PASSWORD:
            params["password"] = cls.REDIS_PASSWORD
        return params

    @classmethod
    def get_performance_config(cls) -> Dict[str, Any]:
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
        return {
            "work_mem": cls.DB_WORK_MEM,
            "maintenance_work_mem": cls.DB_MAINTENANCE_WORK_MEM,
            "synchronous_commit": cls.DB_SYNCHRONOUS_COMMIT,
        }

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        return {
            "postgres_host": cls.POSTGRES_HOST,
            "postgres_port": cls.POSTGRES_PORT,
            "postgres_db": cls.POSTGRES_DB,
            "postgres_user": cls.POSTGRES_USER,
            "postgres_sslrootcert": cls.INTERNAL_CA_CERT,
            "redis_host": cls.REDIS_HOST,
            "redis_port": cls.REDIS_PORT,
            "regtech_base_url": cls.REGTECH_BASE_URL,
            "collection_interval": cls.COLLECTION_INTERVAL,
            "batch_size": cls.BATCH_SIZE,
            "page_size": cls.PAGE_SIZE,
            "max_pages_per_collection": cls.MAX_PAGES_PER_COLLECTION,
            "connection_pool_size": cls.CONNECTION_POOL_SIZE,
            "max_memory_items": cls.MAX_MEMORY_ITEMS,
            "cache_ttl_seconds": cls.CACHE_TTL_SECONDS,
            "auth_cache_ttl_seconds": cls.AUTH_CACHE_TTL_SECONDS,
            "data_cache_max_size": cls.DATA_CACHE_MAX_SIZE,
            "request_timeout": cls.REQUEST_TIMEOUT,
            "max_concurrent_requests": cls.MAX_CONCURRENT_REQUESTS,
            "retry_backoff_factor": cls.RETRY_BACKOFF_FACTOR,
            "enable_performance_metrics": cls.ENABLE_PERFORMANCE_METRICS,
            "metrics_collection_interval": cls.METRICS_COLLECTION_INTERVAL,
            "log_level": cls.LOG_LEVEL,
        }

    @classmethod
    def validate_config(cls) -> bool:
        if not all((cls.POSTGRES_HOST, cls.POSTGRES_DB, cls.POSTGRES_USER, cls.POSTGRES_PASSWORD)):
            return False

        if not 0 < cls.BATCH_SIZE <= 10000:
            return False

        return 0 < cls.PAGE_SIZE <= 5000
