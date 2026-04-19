"""Database helpers for SecureCredentialService."""

from __future__ import annotations

from typing import Any


def get_database_connection(service: Any) -> Any:
    """Return a database connection or raise on failure."""
    conn = None
    if service.db_service:
        conn = service.db_service.get_connection()
    else:
        try:
            from ..database_service import DatabaseService

            db_service = DatabaseService()
            conn = db_service.get_connection()
        except ImportError:
            from core.services.database_service import DatabaseService

            db_service = DatabaseService()
            conn = db_service.get_connection()

    if conn is None:
        raise RuntimeError("Failed to establish database connection")
    return conn


def close_connection(service: Any, conn: Any, logger: Any) -> None:
    """Return a pooled connection or close a standalone connection."""
    if service.db_service:
        service.db_service.return_connection(conn)
        return

    try:
        conn.close()
    except Exception as exc:
        logger.debug("Failed to close connection: %s", exc)
