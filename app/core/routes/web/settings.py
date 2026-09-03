"""
Settings Management Routes
API endpoints for managing system settings
"""

from flask import Blueprint, request, jsonify, render_template, current_app
import logging
from datetime import datetime

from core.auth.decorators import public
from ...services.settings_service import settings_service
from ...services.database_lease import connection_lease
# from ...services.database_service import DatabaseService

logger = logging.getLogger(__name__)

# Create Blueprint
settings_bp = Blueprint("settings", __name__, url_prefix="/settings")
# db_service = DatabaseService()


@settings_bp.route("/")
def settings_page():
    """Settings management UI page"""
    try:
        return render_template("settings.html")
    except Exception as e:
        logger.error(f"Error rendering settings page: {e}")
        return f"Error: {str(e)}", 500


@settings_bp.route("/api/settings", methods=["GET"])
def get_all_settings():
    """
    Get all system settings
    Query params:
        - category: Filter by category (optional)
        - include_encrypted: Include decrypted values (default: false)
    """
    try:
        category = request.args.get("category")
        include_encrypted = request.args.get("include_encrypted", "false").lower() == "true"

        settings = settings_service.get_all_settings(category=category, include_encrypted=include_encrypted)

        return jsonify({"success": True, "count": len(settings), "settings": settings})

    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/api/settings/grouped", methods=["GET"])
def get_settings_grouped():
    """Get all settings grouped by category"""
    try:
        grouped = settings_service.get_settings_by_category()

        return jsonify({"success": True, "categories": list(grouped.keys()), "settings": grouped})

    except Exception as e:
        logger.error(f"Error getting grouped settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/api/settings/<key>", methods=["GET"])
def get_setting(key):
    """Get a specific setting by key"""
    try:
        value = settings_service.get_setting(key)

        if value is None:
            return jsonify({"success": False, "error": f"Setting not found: {key}"}), 404

        return jsonify({"success": True, "key": key, "value": value})

    except Exception as e:
        logger.error(f"Error getting setting {key}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/api/settings/<key>", methods=["PUT"])
def update_setting(key):
    """
    Update a setting value
    Body: { "value": "...", "encrypt": false }
    """
    try:
        data = request.get_json()

        if not data or "value" not in data:
            return jsonify({"success": False, "error": "Missing value in request body"}), 400

        value = data["value"]
        encrypt = data.get("encrypt", False)

        success = settings_service.set_setting(key, value, encrypt=encrypt)

        if success:
            return jsonify({"success": True, "key": key, "message": "Setting updated successfully"})
        else:
            return jsonify({"success": False, "error": "Failed to update setting"}), 500

    except Exception as e:
        logger.error(f"Error updating setting {key}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/api/settings", methods=["POST"])
def create_setting():
    """
    Create a new setting
    Body: {
        "key": "...",
        "value": "...",
        "type": "string|integer|boolean|json|password",
        "description": "...",
        "category": "general|collection|security|notification|integration",
        "encrypt": false
    }
    """
    try:
        data = request.get_json()

        required_fields = ["key", "value", "type"]
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

        success = settings_service.create_setting(
            key=data["key"],
            value=data["value"],
            setting_type=data["type"],
            description=data.get("description", ""),
            category=data.get("category", "general"),
            encrypt=data.get("encrypt", False),
        )

        if success:
            return jsonify(
                {
                    "success": True,
                    "key": data["key"],
                    "message": "Setting created successfully",
                }
            ), 201
        else:
            return jsonify({"success": False, "error": "Failed to create setting"}), 500

    except Exception as e:
        logger.error(f"Error creating setting: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/api/settings/<key>", methods=["DELETE"])
def delete_setting(key):
    """Soft delete a setting (set is_active = false)"""
    try:
        success = settings_service.delete_setting(key)

        if success:
            return jsonify({"success": True, "key": key, "message": "Setting deleted successfully"})
        else:
            return jsonify({"success": False, "error": "Setting not found or already deleted"}), 404

    except Exception as e:
        logger.error(f"Error deleting setting {key}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/api/settings/batch", methods=["PUT"])
def batch_update_settings():
    """
    Batch update multiple settings
    Body: {
        "settings": [
            {"key": "...", "value": "...", "encrypt": false},
            ...
        ]
    }
    """
    try:
        data = request.get_json()

        if not data or "settings" not in data:
            return jsonify({"success": False, "error": "Missing settings array in request body"}), 400

        results = []
        failed = []

        for setting in data["settings"]:
            if "key" not in setting or "value" not in setting:
                failed.append({"setting": setting, "error": "Missing key or value"})
                continue

            success = settings_service.set_setting(
                setting["key"], setting["value"], encrypt=setting.get("encrypt", False)
            )

            if success:
                results.append(setting["key"])
            else:
                failed.append({"key": setting["key"], "error": "Update failed"})

        return jsonify(
            {
                "success": len(failed) == 0,
                "updated": results,
                "failed": failed,
                "total": len(data["settings"]),
                "success_count": len(results),
                "fail_count": len(failed),
            }
        )

    except Exception as e:
        logger.error(f"Error batch updating settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =====================================================
# Credentials Management (Extended)
# =====================================================


@settings_bp.route("/api/credentials", methods=["GET"])
def get_all_credentials():
    """Get all collection credentials"""
    try:
        db_service = current_app.extensions["db_service"]
        with connection_lease(db_service) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT service_name, username, is_active, created_at, updated_at, config
                FROM collection_credentials
                ORDER BY service_name
            """)
            rows = cursor.fetchall()
            cursor.close()

        credentials = []
        for row in rows:
            credentials.append(
                {
                    "service_name": row[0],
                    "username": row[1],
                    "password": "********",  # Never expose password
                    "is_active": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "updated_at": row[4].isoformat() if row[4] else None,
                    "config": row[5] if row[5] else {},
                }
            )

        return jsonify({"success": True, "count": len(credentials), "credentials": credentials})

    except Exception as e:
        logger.error(f"Error getting credentials: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/api/credentials/<service_name>", methods=["PUT"])
def update_credentials(service_name):
    """
    Update collection credentials
    Body: {
        "username": "...",
        "password": "...",
        "config": {...}
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "Missing request body"}), 400

        db_service = current_app.extensions["db_service"]
        update_fields = []
        params = []

        if "username" in data:
            update_fields.append("username = %s")
            params.append(data["username"])

        if "password" in data:
            update_fields.append("password = %s")
            params.append(data["password"])

        if "config" in data:
            update_fields.append("config = %s")
            params.append(data["config"])

        if "is_active" in data:
            update_fields.append("is_active = %s")
            params.append(data["is_active"])

        if not update_fields:
            return jsonify({"success": False, "error": "No fields to update"}), 400

        # Add updated_at
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(service_name)

        query = f"""
            UPDATE collection_credentials
            SET {", ".join(update_fields)}
            WHERE service_name = %s
            RETURNING service_name
        """
        with connection_lease(db_service) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()
            conn.commit()
            cursor.close()

        if result:
            logger.info(f"Credentials updated: {service_name}")
            return jsonify(
                {
                    "success": True,
                    "service_name": service_name,
                    "message": "Credentials updated successfully",
                }
            )
        else:
            return jsonify({"success": False, "error": f"Service not found: {service_name}"}), 404

    except Exception as e:
        logger.error(f"Error updating credentials for {service_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_bp.route("/api/credentials", methods=["POST"])
def create_credentials():
    """
    Create new collection credentials
    Body: {
        "service_name": "...",
        "username": "...",
        "password": "...",
        "config": {...}
    }
    """
    try:
        data = request.get_json()

        required_fields = ["service_name", "username", "password"]
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

        db_service = current_app.extensions["db_service"]
        with connection_lease(db_service) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO collection_credentials
                (service_name, username, password, config, is_active)
                VALUES (%s, %s, %s, %s, true)
                ON CONFLICT (service_name) DO UPDATE
                SET username = EXCLUDED.username,
                    password = EXCLUDED.password,
                    config = EXCLUDED.config,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING service_name
                """,
                (
                    data["service_name"],
                    data["username"],
                    data["password"],
                    data.get("config", {}),
                ),
            )
            result = cursor.fetchone()
            conn.commit()
            cursor.close()

        if result:
            logger.info(f"Credentials created/updated: {data['service_name']}")
            return jsonify(
                {
                    "success": True,
                    "service_name": data["service_name"],
                    "message": "Credentials saved successfully",
                }
            ), 201
        else:
            return jsonify({"success": False, "error": "Failed to save credentials"}), 500

    except Exception as e:
        logger.error(f"Error creating credentials: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Health check
@settings_bp.route("/api/health", methods=["GET"])
@public
def settings_health():
    """Health check for settings service"""
    try:
        # Test database connection (simple query)
        db_service = current_app.extensions["db_service"]
        with connection_lease(db_service) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()

        return jsonify(
            {
                "success": True,
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Settings health check failed: {e}")
        return jsonify(
            {
                "success": False,
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
            }
        ), 500
