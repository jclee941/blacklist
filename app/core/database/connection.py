"""
데이터베이스 연결 관리
"""

import psycopg2
from psycopg2.extras import RealDictCursor

from ..config import config


def _get_connection_params():
    return config.get_postgres_params()


def get_db_connection():
    """데이터베이스 연결 생성"""
    params = _get_connection_params()
    return psycopg2.connect(
        **params,
        cursor_factory=RealDictCursor,
    )
