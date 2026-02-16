"""
데이터베이스 연결 관리
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging

from ..config import config

logger = logging.getLogger(__name__)


def _get_connection_params():
    return config.get_postgres_params()


def get_db_connection():
    """데이터베이스 연결 생성"""
    params = _get_connection_params()
    return psycopg2.connect(
        host=params["host"],
        port=params["port"],
        database=params["database"],
        user=params["user"],
        password=params["password"],
        cursor_factory=RealDictCursor,
    )
