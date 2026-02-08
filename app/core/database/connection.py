"""
데이터베이스 연결 관리
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)


def get_db_connection():
    """데이터베이스 연결 생성"""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "blacklist-postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "blacklist"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        cursor_factory=RealDictCursor,
    )
