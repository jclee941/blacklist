"""
데이터베이스 연결 관리
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def _get_connection_params():
    database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

    if database_url:
        parsed = urlparse(database_url)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip("/") or "blacklist",
            "user": parsed.username or "postgres",
            "password": parsed.password or "postgres",
        }

    return {
        "host": os.getenv("POSTGRES_HOST", "blacklist-postgres"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "blacklist"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    }


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
