"""
실제 PostgreSQL 데이터베이스 연동 서비스
NextTrade Blacklist Management System용 데이터베이스 접근 계층
"""

import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from typing import Dict, Optional, Any
import time

from ..config import config
from ..utils.logger_config import db_logger as logger


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

    def _initialize_pool_with_retry(self, max_retries: int = 10, base_delay: float = 2.0):
        """Initialize connection pool with exponential backoff retry for Watchtower resilience"""
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

    def get_connection(self):
        """Get connection from pool with automatic retry on failure"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                if not self.connection_pool:
                    self._initialize_pool_with_retry()

                return self.connection_pool.getconn()

            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"⚠️ Failed to get connection (attempt {retry_count}/{max_retries}): {e}")
                    time.sleep(1)
                    # Try to reinitialize pool
                    try:
                        self._initialize_pool_with_retry()
                    except Exception as init_error:
                        logger.error(f"❌ Pool reinitialization failed: {init_error}")
                else:
                    logger.error(f"❌ Failed to get connection after {max_retries} attempts: {e}")
                    raise

    def return_connection(self, conn):
        """Return connection to pool"""
        try:
            if self.connection_pool and conn:
                self.connection_pool.putconn(conn)
        except Exception as e:
            logger.warning(f"Failed to return connection to pool: {e}")
            # Connection may belong to a stale pool after reinitialization;
            # close it directly to prevent connection leaks.
            try:
                if conn and not conn.closed:
                    conn.close()
            except Exception as e:
                logger.debug("Failed to close leaked connection: %s", e)

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
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            self.return_connection(conn)
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

    def query(self, sql: str, params=None) -> list:
        """Execute a SELECT query and return results as list of dicts"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            results = cursor.fetchall()
            cursor.close()
            self.return_connection(conn)
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
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            affected_rows = cursor.rowcount
            conn.commit()
            cursor.close()
            self.return_connection(conn)
            return affected_rows
        except Exception as e:
            logger.error(f"Execute query failed: {e}")
            try:
                if conn:
                    conn.rollback()
            except Exception as e:
                logger.debug("Rollback failed during error handling: %s", e)
            raise

    def create_raw_connection(self):
        """
        Create a new raw database connection (bypassing the pool)
        Useful for special operations like LISTEN/NOTIFY or maintenance
        """
        try:
            return psycopg2.connect(**self.db_config)
        except Exception as e:
            logger.error(f"Failed to create raw connection: {e}")
            raise

    def save_blacklist_ip(self, ip_data: dict) -> bool:
        """Save blacklist IP data to database"""
        conn = None
        try:
            conn = self.get_connection()
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
            self.return_connection(conn)
            return True

        except Exception as e:
            logger.error(f"Failed to save blacklist IP {ip_data.get('ip_address', 'unknown')}: {e}")
            try:
                if conn:
                    conn.rollback()
                    self.return_connection(conn)
            except BaseException as e:
                logger.debug("Cleanup rollback failed: %s", e)
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
                conn = self.get_connection()
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT service_name, username, password, config, created_at, updated_at
                    FROM collection_credentials
                    WHERE service_name = %s AND is_active = true
                """,
                    (service_name.upper(),),
                )

                result = cursor.fetchone()
                cursor.close()
                self.return_connection(conn)

                if result:
                    (
                        service_name_db,
                        username,
                        password,
                        config,
                        created_at,
                        updated_at,
                    ) = result
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
            conn = self.get_connection()
            cursor = conn.cursor()

            # 1. 모든 테이블 목록 조회 (중복 제거)
            cursor.execute("""
                SELECT DISTINCT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)

            tables = {}
            table_list = cursor.fetchall()

            for (table_name,) in table_list:
                try:
                    # 2. 컬럼 정보 조회
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

                    # 3. Record count query (using sql.Identifier for safe table name)
                    cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name)))
                    record_count = cursor.fetchone()[0]

                    tables[table_name] = {
                        "columns": columns,
                        "record_count": record_count,
                    }

                except Exception as table_error:
                    logger.error(f"Error processing table {table_name}: {table_error}")
                    tables[table_name] = {
                        "columns": [],
                        "record_count": 0,
                        "error": str(table_error),
                    }

            cursor.close()
            self.return_connection(conn)

            return {"success": True, "total_tables": len(tables), "tables": tables}

        except Exception as e:
            logger.error(f"❌ show_database_tables 실패: {e}")
            return {"success": False, "error": str(e), "tables": {}}

    def get_blacklist_stats(self) -> Dict[str, Any]:
        """블랙리스트 통계 조회"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Total IPs
            cursor.execute("SELECT COUNT(*) FROM blacklist_ips")
            total_ips = cursor.fetchone()[0]

            # Active IPs
            cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE is_active = true")
            active_ips = cursor.fetchone()[0]

            # Last update
            cursor.execute("""
                SELECT MAX(updated_at) FROM blacklist_ips
            """)
            last_update_result = cursor.fetchone()[0]
            last_update = last_update_result.strftime("%Y-%m-%d %H:%M") if last_update_result else "없음"

            cursor.close()
            self.return_connection(conn)

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
            conn = self.get_connection()
            cursor = conn.cursor()

            # Total IPs
            cursor.execute("SELECT COUNT(*) FROM blacklist_ips")
            total_count = cursor.fetchone()[0]

            # REGTECH source IPs
            cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE data_source = 'REGTECH'")
            regtech_count = cursor.fetchone()[0]

            # Last collection
            cursor.execute("""
                SELECT MAX(collection_date) FROM collection_history
            """)
            last_collection_result = cursor.fetchone()[0]
            last_updated = last_collection_result.strftime("%Y-%m-%d %H:%M") if last_collection_result else "확인 중..."

            cursor.close()
            self.return_connection(conn)

            return {
                "total_count": total_count,
                "regtech_count": regtech_count,
                "last_updated": last_updated,
            }

        except Exception as e:
            logger.error(f"대시보드 통계 조회 실패: {e}")
            return {"total_count": 0, "regtech_count": 0, "last_updated": "오류"}
