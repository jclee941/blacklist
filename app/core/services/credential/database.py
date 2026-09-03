"""Database helpers for SecureCredentialService."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any

from psycopg2.extensions import connection as PostgreSQLConnection

from ..database_lease import connection_lease


def get_database_connection(service: Any) -> AbstractContextManager[PostgreSQLConnection]:
    """Return a deterministic lease for the configured database service."""
    if service.db_service:
        return connection_lease(service.db_service)

    try:
        from ..database_service import DatabaseService
    except ImportError:
        from core.services.database_service import DatabaseService

    return connection_lease(DatabaseService())
