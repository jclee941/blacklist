"""
Database Schema and Table Browser API
Provides database schema information and table browsing functionality

Updated: 2025-11-21 (Error Handling Standardization - HIGH PRIORITY #4)
Reference: docs/104-ERROR-HANDLING-STANDARDIZATION-PLAN.md
"""

from flask import Blueprint, jsonify, request, g, current_app
from datetime import datetime
import logging
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
from ...exceptions import (
    BadRequestError,
    ValidationError,
    DatabaseError,
)

logger = logging.getLogger(__name__)

database_api_bp = Blueprint("database_api", __name__, url_prefix="/database")


@database_api_bp.route("/connection", methods=["GET"])
def get_connection_status():
    """
    Get database connection status

    GET /api/database/connection

    Returns:
        {
            "success": True,
            "data": {
                "connected": True,
                "pool_size": 10,
                "pool_used": 2
            }
        }
    """
    try:
        db_service = current_app.extensions["db_service"]
        status = db_service.get_connection_status()
        return jsonify({"success": True, "data": status, "timestamp": datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"Connection status check failed: {e}")
        raise DatabaseError(message="Failed to get connection status", query="connection_status_check")


@database_api_bp.route("/schema", methods=["GET"])
def get_database_schema():
    """
    Query database schema information (Phase 1.4: Standardized Error Handling)

    GET /api/database/schema

    Returns:
        {
            "success": True,
            "data": {
                "tables": [...],
                "total": 10
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        DatabaseError: Database query failed
    """
    try:
        db_service = current_app.extensions["db_service"]

        # Query table list and row counts
        tables = db_service.query("""
            SELECT
                table_name as name,
                (SELECT COUNT(*) FROM information_schema.columns
                 WHERE table_name = t.table_name AND table_schema = 'public') as column_count,
                pg_class.reltuples::bigint as row_count
            FROM information_schema.tables t
            LEFT JOIN pg_class ON pg_class.relname = t.table_name
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        return jsonify(
            {
                "success": True,
                "data": {"tables": tables, "total": len(tables)},
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Schema query error: {e}", exc_info=True)
        raise DatabaseError(
            message="Failed to retrieve database schema",
            details={"error_type": type(e).__name__},
        )


@database_api_bp.route("/table/<table_name>", methods=["GET"])
def get_table_data(table_name: str):
    """
    Query specific table data with pagination (Phase 1.4: Standardized Error Handling)

    GET /api/database/table/{table_name}?page=1&limit=50

    Returns:
        {
            "success": True,
            "data": {
                "table_name": "blacklist_ips",
                "columns": [...],
                "rows": [...],
                "pagination": {...}
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        BadRequestError: Table not allowed
        ValidationError: Invalid pagination parameters
        DatabaseError: Database query failed
    """
    # SQL Injection prevention: only allow whitelisted tables
    allowed_tables = [
        "blacklist_ips",
        "whitelist_ips",
        "collection_credentials",
        "collection_history",
        "collection_status",
        "system_logs",
        "monitoring_data",
        "pipeline_metrics",
        "collection_metrics",
    ]

    if table_name not in allowed_tables:
        raise BadRequestError(
            message=f"Table '{table_name}' is not allowed for querying",
            details={"table": table_name, "allowed_tables": allowed_tables},
        )

    # Get and validate pagination parameters
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 50))
    except ValueError as e:
        raise ValidationError(
            message="Page and limit must be valid integers",
            field="page/limit",
            details={"error": str(e)},
        )

    # Validate pagination ranges
    if page < 1:
        raise ValidationError(
            message="Page number must be >= 1",
            field="page",
            details={"provided_value": page},
        )
    if limit < 1 or limit > 1000:
        raise ValidationError(
            message="Limit must be between 1 and 1000",
            field="limit",
            details={"provided_value": limit, "allowed_range": "1-1000"},
        )

    try:
        offset = (page - 1) * limit

        db_service = current_app.extensions["db_service"]
        conn = db_service.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Total row count (using sql.Identifier for safe table name interpolation)
            cursor.execute(sql.SQL("SELECT COUNT(*) as total FROM {}").format(sql.Identifier(table_name)))
            total = cursor.fetchone()["total"]

            # Column list (filter hidden columns for UI)
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """,
                (table_name,),
            )

            # Hide specified columns from UI
            hidden_columns = [
                "created_at",
                "registered_at",
                "confidence_level",
                "updated_at",
            ]
            all_columns = [row["column_name"] for row in cursor.fetchall()]
            columns = [col for col in all_columns if col not in hidden_columns]

            # Query data (using sql.Identifier for safe table name)
            cursor.execute(
                sql.SQL("""
                    SELECT * FROM {}
                    ORDER BY
                        CASE WHEN EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = %s AND column_name = 'created_at'
                        ) THEN created_at END DESC,
                        CASE WHEN EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = %s AND column_name = 'id'
                        ) THEN id END DESC
                    LIMIT %s OFFSET %s
                """).format(sql.Identifier(table_name)),
                (table_name, table_name, limit, offset),
            )

            data = cursor.fetchall()

            # Convert data for JSON serialization and filter hidden columns
            serialized_data = []
            for row in data:
                row_dict = dict(row)
                # Remove hidden columns from response
                for hidden_col in hidden_columns:
                    row_dict.pop(hidden_col, None)
                # Convert datetime objects to ISO format
                for key, value in row_dict.items():
                    if hasattr(value, "isoformat"):
                        row_dict[key] = value.isoformat()
                    # JSONB fields remain as dict
                serialized_data.append(row_dict)

        finally:
            cursor.close()
            db_service.return_connection(conn)

        return jsonify(
            {
                "success": True,
                "data": {
                    "table_name": table_name,
                    "columns": columns,
                    "rows": serialized_data,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "limit": limit,
                        "total_pages": (total + limit - 1) // limit,
                    },
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except BadRequestError:
        raise  # Re-raise access control errors
    except ValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"Table data query error for {table_name}: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to retrieve data from table '{table_name}'",
            details={
                "table": table_name,
                "page": page,
                "limit": limit,
                "error_type": type(e).__name__,
            },
        )


@database_api_bp.route("/table/<table_name>/column/<column_name>", methods=["GET"])
def get_column_stats(table_name: str, column_name: str):
    """
    Get statistics for specific column (Phase 1.4: Standardized Error Handling)

    GET /api/database/table/{table_name}/column/{column_name}

    Returns:
        {
            "success": True,
            "data": {
                "table_name": "blacklist_ips",
                "column_name": "ip_address",
                "stats": {
                    "total_rows": 1234,
                    "non_null_count": 1234,
                    "distinct_count": 1234
                }
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        BadRequestError: Table not allowed
        DatabaseError: Database query failed
    """
    # SQL Injection prevention: only allow whitelisted tables
    allowed_tables = [
        "blacklist_ips",
        "whitelist_ips",
        "collection_credentials",
        "collection_history",
        "collection_status",
        "system_logs",
        "monitoring_data",
        "pipeline_metrics",
        "collection_metrics",
    ]

    if table_name not in allowed_tables:
        raise BadRequestError(
            message=f"Table '{table_name}' is not allowed for querying",
            details={"table": table_name, "allowed_tables": allowed_tables},
        )

    try:
        db_service = current_app.extensions["db_service"]
        conn = db_service.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Column statistics (using sql.Identifier for safe interpolation)
            cursor.execute(
                sql.SQL("""
                    SELECT
                        COUNT(*) as total_rows,
                        COUNT({}) as non_null_count,
                        COUNT(DISTINCT {}) as distinct_count
                    FROM {}
                """).format(
                    sql.Identifier(column_name),
                    sql.Identifier(column_name),
                    sql.Identifier(table_name),
                )
            )

            stats = cursor.fetchone()
        finally:
            cursor.close()
            db_service.return_connection(conn)

        return jsonify(
            {
                "success": True,
                "data": {
                    "table_name": table_name,
                    "column_name": column_name,
                    "stats": stats,
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Column stats error for {table_name}.{column_name}: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to retrieve statistics for column '{column_name}' in table '{table_name}'",
            details={
                "table": table_name,
                "column": column_name,
                "error_type": type(e).__name__,
            },
        )
