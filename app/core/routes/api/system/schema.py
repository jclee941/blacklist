"""Database schema endpoints for the shared system API blueprint."""

from . import common
from ....services.database_lease import connection_lease


@common.api_bp.route("/database/schema", methods=["GET"])
def get_database_schema():
    """
    데이터베이스 스키마 정보 (Phase 1.4: Standardized Error Handling)

    GET /api/database/schema

    Returns:
        {
            "success": True,
            "data": {
                "schema": {...},
                "total_tables": 10
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        DatabaseError: Schema query failed
    """
    try:
        db_service = common.current_app.extensions["db_service"]
        with connection_lease(db_service) as conn:
            cursor = conn.cursor(cursor_factory=common.RealDictCursor)
            cursor.execute(
                """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """
            )

            schema_info = {}
            for row in cursor.fetchall():
                table = row["table_name"]
                if table not in schema_info:
                    schema_info[table] = []

                schema_info[table].append(
                    {
                        "column": row["column_name"],
                        "type": row["data_type"],
                        "nullable": row["is_nullable"] == "YES",
                    }
                )

            cursor.close()

        return common.jsonify(
            {
                "success": True,
                "data": {"schema": schema_info, "total_tables": len(schema_info)},
                "timestamp": common.datetime.now().isoformat(),
                "request_id": common.g.request_id,
            }
        ), 200

    except Exception as e:
        common.logger.error(f"Database schema error: {e}", exc_info=True)
        raise common.database_error_cls(
            message="Failed to retrieve database schema",
            details={"error_type": type(e).__name__},
        )


@common.api_bp.route("/database/schema/update", methods=["POST"])
def update_database_schema():
    """
    데이터베이스 스키마 업데이트 (Phase 1.4: Standardized Error Handling)

    POST /api/database/schema/update

    Returns:
        {
            "success": True,
            "data": {
                "message": "스키마 업데이트 완료",
                "result": {...}
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        DatabaseError: Schema update failed
    """
    try:
        db_service = common.current_app.extensions["db_service"]
        result = db_service.update_schema()

        return common.jsonify(
            {
                "success": True,
                "data": {"message": "스키마 업데이트 완료", "result": result},
                "timestamp": common.datetime.now().isoformat(),
                "request_id": common.g.request_id,
            }
        ), 200

    except Exception as e:
        common.logger.error(f"Schema update error: {e}", exc_info=True)
        raise common.database_error_cls(
            message="Failed to update database schema",
            details={"error_type": type(e).__name__},
        )


@common.api_bp.route("/database/schema/fix", methods=["POST"])
def fix_schema_force():
    """
    강제 스키마 수정 (Phase 1.4: Standardized Error Handling)

    POST /api/database/schema/fix

    Returns:
        {
            "success": True,
            "data": {
                "message": "스키마 강제 수정 완료",
                "columns_added": ["country", "detection_date", "removal_date"]
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        DatabaseError: Schema modification failed
    """
    try:
        db_service = common.current_app.extensions["db_service"]

        queries = [
            "ALTER TABLE blacklist_ips ADD COLUMN IF NOT EXISTS country VARCHAR(10)",
            "ALTER TABLE blacklist_ips ADD COLUMN IF NOT EXISTS detection_date DATE",
            "ALTER TABLE blacklist_ips ADD COLUMN IF NOT EXISTS removal_date DATE",
        ]

        for query in queries:
            db_service.execute_query(query)

        return common.jsonify(
            {
                "success": True,
                "data": {
                    "message": "스키마 강제 수정 완료",
                    "columns_added": ["country", "detection_date", "removal_date"],
                },
                "timestamp": common.datetime.now().isoformat(),
                "request_id": common.g.request_id,
            }
        ), 200

    except Exception as e:
        common.logger.error(f"Force schema fix error: {e}", exc_info=True)
        raise common.database_error_cls(
            message="Failed to apply forced schema modifications",
            details={"error_type": type(e).__name__},
        )
