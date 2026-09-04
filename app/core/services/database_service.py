"""
실제 PostgreSQL 데이터베이스 연동 서비스
NextTrade Blacklist Management System용 데이터베이스 접근 계층
"""

import psycopg2
from contextlib import AbstractContextManager
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PostgreSQLConnection
from typing import Dict, Optional, Any
import time

from ..config import config
from ..utils.logger_config import db_logger as logger
from .database_lease import connection_lease

MAX_STARTUP_RETRIES = 5
MAX_STARTUP_BACKOFF_SECONDS = 1.0


class DatabaseService:
    """Database service with connection pooling and retry logic for dependency resilience"""

    def __init__(self):
        self.connection_pool: Optional[pool.ThreadedConnectionPool] = None
        self.db_config = config.get_postgres_params()
        self.max_retries = config.DB_CONNECT_RETRIES
        self.base_delay = config.DB_BACKOFF_DELAY
        if config.TESTING and not config.USE_REAL_DB:
            self.connection_pool = None  # Ensure it's explicitly None in testing
            logger.info("✅ DatabaseService initialized in TESTING mode (no real connection)")
        else:
            self._initialize_pool_with_retry(max_retries=self.max_retries, base_delay=self.base_delay)

    def _initialize_pool_with_retry(
        self,
        max_retries: int = MAX_STARTUP_RETRIES,
        base_delay: float = MAX_STARTUP_BACKOFF_SECONDS,
    ):
        """Initialize connection pool with exponential backoff retry for Watchtower resilience"""
        max_retries = min(max_retries, MAX_STARTUP_RETRIES)
        base_delay = min(base_delay, MAX_STARTUP_BACKOFF_SECONDS)
        retry_count = 0

        while retry_count < max_retries:
            try:
                if self.connection_pool:
                    self.connection_pool.closeall()

                self.connection_pool = pool.ThreadedConnectionPool(minconn=3, maxconn=8, **self.db_config)

                # Test connection
                test_conn = self.connection_pool.getconn()
                test_conn.cursor().execute("SELECT 1")
                self.connection_pool.putconn(test_conn)
                self._apply_schema_migrations()

                logger.info(f"✅ Database connection pool initialized successfully (attempt {retry_count + 1})")
                return

            except Exception as e:
                retry_count += 1
                delay = base_delay * (2 ** (retry_count - 1))  # Exponential backoff

                if retry_count < max_retries:
                    logger.warning(f"⚠️ Database connection failed (attempt {retry_count}/{max_retries}): {e}")
                    logger.info(f"🔄 Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"❌ Database connection failed after {max_retries} attempts: {e}")
                    raise

    def _apply_schema_migrations(self) -> None:
        with self.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                ALTER TABLE whitelist_ips
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

                UPDATE whitelist_ips
                SET is_active = TRUE
                WHERE is_active IS NULL;

                ALTER TABLE whitelist_ips
                ALTER COLUMN is_active SET DEFAULT TRUE;

                ALTER TABLE whitelist_ips
                ALTER COLUMN is_active SET NOT NULL;

                ALTER TABLE blacklist_ips
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

                UPDATE blacklist_ips
                SET is_active = TRUE
                WHERE is_active IS NULL;

                ALTER TABLE blacklist_ips
                ALTER COLUMN is_active SET DEFAULT TRUE;

                ALTER TABLE blacklist_ips
                ALTER COLUMN is_active SET NOT NULL;

                CREATE UNIQUE INDEX IF NOT EXISTS idx_whitelist_ips_ip_unique
                ON whitelist_ips(ip_address);

                CREATE UNIQUE INDEX IF NOT EXISTS idx_blacklist_ips_ip_source_unique
                ON blacklist_ips(ip_address, source);

                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = current_user AND rolsuper) THEN
                        EXECUTE format(
                            'ALTER ROLE %I NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION',
                            current_user
                        );
                    END IF;
                END
                $$;
                """
            )
            connection.commit()
            cursor.close()

    def get_connection(self) -> PostgreSQLConnection:
        """Get connection from pool with automatic retry on failure"""
        max_retries = 3
        retry_count = 0

        if not self.connection_pool:
            self._initialize_pool_with_retry()
        connection_pool = self.connection_pool
        if connection_pool is None:
            raise RuntimeError("Database connection pool is unavailable")

        while retry_count < max_retries:
            try:
                return connection_pool.getconn()

            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"⚠️ Failed to get connection (attempt {retry_count}/{max_retries}): {e}")
                    time.sleep(1)
                else:
                    logger.error(f"❌ Failed to get connection after {max_retries} attempts: {e}")
                    raise
        raise RuntimeError("Database connection checkout failed")

    def connection(self) -> AbstractContextManager[PostgreSQLConnection]:
        """Lease a pooled connection and return it deterministically."""
        return connection_lease(self)

    def return_connection(self, connection: PostgreSQLConnection) -> None:
        """Return connection to pool"""
        try:
            if self.connection_pool and connection:
                self.connection_pool.putconn(connection)
        except Exception as e:
            logger.warning(f"Failed to return connection to pool: {e}")
            try:
                if self.connection_pool:
                    self.connection_pool.putconn(connection, close=True)
            except Exception as close_error:
                logger.debug("Failed to discard stale pooled connection: %s", close_error)

    def close_all_connections(self):
        """Close all connections in pool"""
        try:
            if self.connection_pool:
                self.connection_pool.closeall()
                self.connection_pool = None
                logger.info("All database connections closed")
        except Exception as e:
            logger.error(f"Error closing connections: {e}")

    def health_check(self) -> bool:
        """Health check with retry logic"""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
            return result is not None
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status for API endpoint"""
        try:
            is_healthy = self.health_check()
            pool_info = {}
            if self.connection_pool:
                pool_info = {
                    "min_connections": self.connection_pool.minconn,
                    "max_connections": self.connection_pool.maxconn,
                }
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "host": self.db_config.get("host"),
                "port": self.db_config.get("port"),
                "database": self.db_config.get("database"),
                "pool": pool_info,
            }
        except Exception as e:
            logger.error(f"Connection status check failed: {e}")
            return {"status": "error", "error": str(e)}

    def query(self, sql: str, params=None) -> list[dict[str, Any]]:
        """Execute a SELECT query and return results as list of dicts"""
        try:
            with self.connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                results = cursor.fetchall()
                cursor.close()
            return [dict(row) for row in results] if results else []
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def execute(self, sql: str, params=None) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query and return affected rows

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            Number of affected rows
        """
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                affected_rows = cursor.rowcount
                conn.commit()
                cursor.close()
                return affected_rows
        except Exception as e:
            logger.error(f"Execute query failed: {e}")
            raise

    def create_raw_connection(self):
        """
        Create a new raw database connection (bypassing the pool)
        Useful for special operations like LISTEN/NOTIFY or maintenance
        """
        try:
            return psycopg2.connect(config.get_postgres_dsn())
        except Exception as e:
            logger.error(f"Failed to create raw connection: {e}")
            raise

    def save_blacklist_ip(self, ip_data: dict[str, Any]) -> bool:
        """Save blacklist IP data to database"""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()

                # Insert or update blacklist IP
                cursor.execute(
                    """
                INSERT INTO blacklist_ips (
                    ip_address, source, reason, confidence_level,
                    detection_count, is_active, country, detection_date, removal_date,
                    last_seen, created_at, raw_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ip_address, source) DO UPDATE SET
                    detection_count = blacklist_ips.detection_count + 1,
                    last_seen = EXCLUDED.last_seen,
                    removal_date = COALESCE(EXCLUDED.removal_date,
                        blacklist_ips.removal_date),
                    is_active = CASE
                        WHEN COALESCE(EXCLUDED.removal_date, blacklist_ips.removal_date) <= CURRENT_DATE
                        THEN false
                        ELSE EXCLUDED.is_active
                    END,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = CURRENT_TIMESTAMP
                """,
                    (
                        ip_data.get("ip_address"),
                        ip_data.get("source", "unknown"),
                        ip_data.get("reason"),
                        ip_data.get("confidence_level", 50),
                        ip_data.get("detection_count", 1),
                        ip_data.get("is_active", True),
                        ip_data.get("country"),
                        ip_data.get("detection_date"),
                        ip_data.get("removal_date"),
                        ip_data.get("last_seen"),
                        ip_data.get("created_at", "NOW()"),
                        ip_data.get("raw_data", "{}"),
                    ),
                )

                conn.commit()
                cursor.close()
            return True

        except Exception as e:
            logger.error(f"Failed to save blacklist IP {ip_data.get('ip_address', 'unknown')}: {e}")
            return False

    def get_collection_credentials(self, service_name: str) -> Dict[str, Any]:
        """수집 서비스 인증정보 조회 - 보안 서비스 통합"""
        try:
            from flask import current_app

            svc = current_app.extensions.get("secure_credential_service")
            if svc is None:
                raise RuntimeError("secure_credential_service not initialized")
            credentials = svc.get_credentials(service_name)

            if credentials:
                return {
                    "service_name": service_name,
                    "username": credentials.get("username", ""),
                    "password": credentials.get("password", ""),
                    "config": credentials.get("config", {}),
                    "is_authenticated": bool(credentials.get("username") and credentials.get("password")),
                    "encrypted": credentials.get("encrypted", False),
                    "created_at": credentials.get("created_at"),
                    "updated_at": credentials.get("updated_at"),
                }
            else:
                # 기존 방식으로 폴백 (호환성)
                with self.connection() as conn:
                    cursor = conn.cursor()

                    cursor.execute(
                        """
                    SELECT service_name, username, password, config, encrypted, created_at, updated_at
                    FROM collection_credentials
                    WHERE service_name = %s AND is_active = true
                    """,
                        (service_name.upper(),),
                    )

                    result = cursor.fetchone()
                    cursor.close()

                if result:
                    (
                        service_name_db,
                        username,
                        password,
                        config,
                        encrypted,
                        created_at,
                        updated_at,
                    ) = result
                    if encrypted:
                        logger.error("Encrypted credentials could not be decrypted for %s", service_name)
                        return {"error": "Encrypted credentials could not be decrypted"}
                    return {
                        "service_name": service_name_db,
                        "username": username or "",
                        "password": password or "",
                        "config": config if config else {},
                        "is_authenticated": bool(username and password),
                        "encrypted": False,
                        "created_at": created_at,
                        "updated_at": updated_at,
                    }
                else:
                    logger.warning(f"⚠️ {service_name} 인증정보를 찾을 수 없음")
                    return {"error": f"{service_name} 인증정보가 설정되지 않음"}

        except Exception as e:
            logger.error(f"❌ {service_name} 인증정보 조회 실패: {e}")
            return {"error": str(e)}

    def show_database_tables(self) -> Dict[str, Any]:
        """데이터베이스 테이블 상세 정보 조회 (UI용)"""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_type = 'BASE TABLE'
                      AND table_name <> 'collection_credentials'
                    ORDER BY table_name
                """)
                tables = {}
                table_list = cursor.fetchall()

                for (table_name,) in table_list:
                    try:
                        cursor.execute(
                            """
                            SELECT column_name, data_type, is_nullable
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = %s
                            ORDER BY ordinal_position
                            """,
                            (table_name,),
                        )
                        columns = []
                        for col_name, col_type, nullable in cursor.fetchall():
                            columns.append({"name": col_name, "type": col_type, "nullable": nullable})

                        cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name)))
                        count_row = cursor.fetchone()
                        record_count = count_row[0] if count_row else 0
                        tables[table_name] = {
                            "columns": columns,
                            "record_count": record_count,
                        }

                    except Exception as table_error:
                        logger.error(f"Error processing table {table_name}: {table_error}")
                        tables[table_name] = {
                            "columns": [],
                            "record_count": 0,
                            "error": "Table metadata unavailable",
                        }

                cursor.close()
            return {"success": True, "total_tables": len(tables), "tables": tables}

        except Exception as e:
            logger.error(f"❌ show_database_tables 실패: {e}")
            return {"success": False, "error": "Database metadata unavailable", "tables": {}}

    def get_blacklist_stats(self) -> Dict[str, Any]:
        """블랙리스트 통계 조회"""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()

                # Total IPs
                cursor.execute("SELECT COUNT(*) FROM blacklist_ips")
                total_row = cursor.fetchone()
                total_ips = total_row[0] if total_row else 0

                # Active IPs
                cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE is_active = true")
                active_row = cursor.fetchone()
                active_ips = active_row[0] if active_row else 0

                # Last update
                cursor.execute("""
                SELECT MAX(updated_at) FROM blacklist_ips
            """)
                last_update_row = cursor.fetchone()
                last_update_result = last_update_row[0] if last_update_row else None
                last_update = last_update_result.strftime("%Y-%m-%d %H:%M") if last_update_result else "없음"

                cursor.close()

            return {
                "total_ips": total_ips,
                "active_ips": active_ips,
                "last_update": last_update,
            }

        except Exception as e:
            logger.error(f"블랙리스트 통계 조회 실패: {e}")
            return {"total_ips": 0, "active_ips": 0, "last_update": "오류"}

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """대시보드 통계 조회"""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()

                # Total IPs
                cursor.execute("SELECT COUNT(*) FROM blacklist_ips")
                total_row = cursor.fetchone()
                total_count = total_row[0] if total_row else 0

                # REGTECH source IPs
                cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE data_source = 'REGTECH'")
                regtech_row = cursor.fetchone()
                regtech_count = regtech_row[0] if regtech_row else 0

                # Last collection
                cursor.execute("""
                SELECT MAX(collection_date) FROM collection_history
            """)
                last_collection_row = cursor.fetchone()
                last_collection_result = last_collection_row[0] if last_collection_row else None
                last_updated = (
                    last_collection_result.strftime("%Y-%m-%d %H:%M") if last_collection_result else "확인 중..."
                )

                cursor.close()

            return {
                "total_count": total_count,
                "regtech_count": regtech_count,
                "last_updated": last_updated,
            }

        except Exception as e:
            logger.error(f"대시보드 통계 조회 실패: {e}")
            return {"total_count": 0, "regtech_count": 0, "last_updated": "오류"}
