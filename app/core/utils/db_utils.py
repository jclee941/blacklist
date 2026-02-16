"""
Database utility functions
공통 데이터베이스 연결 및 에러 처리 유틸리티
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Dict, Any, Optional, Generator
import logging

from ..config import config

logger = logging.getLogger(__name__)


def get_db_config() -> Dict[str, str]:
    """데이터베이스 설정 반환 (환경변수 기반)"""
    return config.get_postgres_params()


@contextmanager
def get_db_connection(
    config: Optional[Dict[str, str]] = None, cursor_factory=RealDictCursor
) -> Generator[Any, None, None]:
    """
    데이터베이스 연결 컨텍스트 매니저

    사용 예시:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")

    Args:
        config: 데이터베이스 설정 (None이면 기본값 사용)
        cursor_factory: 커서 팩토리 (기본값: RealDictCursor)

    Yields:
        psycopg2 connection object
    """
    db_config = config or get_db_config()
    conn = None

    try:
        conn = psycopg2.connect(**db_config, cursor_factory=cursor_factory)
        yield conn
        conn.commit()
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Unexpected error in database operation: {e}")
        raise
    finally:
        if conn:
            conn.close()


def execute_query(
    query: str, params: Optional[tuple] = None, fetch_one: bool = False, config: Optional[Dict[str, str]] = None
) -> Any:
    """
    쿼리 실행 헬퍼 함수

    Args:
        query: SQL 쿼리
        params: 쿼리 파라미터
        fetch_one: True이면 fetchone(), False이면 fetchall()
        config: 데이터베이스 설정

    Returns:
        쿼리 결과 (dict 또는 list of dict)
    """
    with get_db_connection(config) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params or ())

        if fetch_one:
            return cursor.fetchone()
        else:
            return cursor.fetchall()


def execute_write(query: str, params: Optional[tuple] = None, config: Optional[Dict[str, str]] = None) -> int:
    """
    INSERT/UPDATE/DELETE 쿼리 실행 헬퍼 함수

    Args:
        query: SQL 쿼리
        params: 쿼리 파라미터
        config: 데이터베이스 설정

    Returns:
        영향받은 행 수
    """
    with get_db_connection(config) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        return cursor.rowcount


def table_exists(table_name: str, config: Optional[Dict[str, str]] = None) -> bool:
    """
    테이블 존재 여부 확인

    Args:
        table_name: 테이블 이름
        config: 데이터베이스 설정

    Returns:
        테이블 존재 여부
    """
    query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = %s
        )
    """

    result = execute_query(query, (table_name,), fetch_one=True, config=config)
    return result["exists"] if result else False
