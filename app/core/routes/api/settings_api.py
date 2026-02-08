"""
Settings API Routes
RESTful API endpoints for system settings management
Accessible at /api/settings (not /settings/api/settings)
"""

from flask import Blueprint, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

settings_api_bp = Blueprint("settings_api", __name__)


@settings_api_bp.route("/settings", methods=["GET"])
@settings_api_bp.route("/settings/all", methods=["GET"])  # Alias for compatibility
def get_all_settings():
    """
    Get all system settings
    Query params:
        - category: Filter by category (optional)
        - include_encrypted: Include decrypted values (default: false)
    """
    try:
        settings_service = current_app.extensions["settings_service"]
        category = request.args.get("category")
        include_encrypted = request.args.get("include_encrypted", "false").lower() == "true"

        settings = settings_service.get_all_settings(category=category, include_encrypted=include_encrypted)

        return jsonify({"success": True, "count": len(settings), "settings": settings})

    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_api_bp.route("/settings/grouped", methods=["GET"])
def get_settings_grouped():
    """Get all settings grouped by category"""
    try:
        settings_service = current_app.extensions["settings_service"]
        grouped = settings_service.get_settings_by_category()

        return jsonify({"success": True, "categories": list(grouped.keys()), "settings": grouped})

    except Exception as e:
        logger.error(f"Error getting grouped settings: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_api_bp.route("/settings/<key>", methods=["GET"])
def get_setting(key):
    """Get a specific setting by key"""
    try:
        settings_service = current_app.extensions["settings_service"]
        value = settings_service.get_setting(key)

        if value is None:
            return jsonify({"success": False, "error": f"Setting not found: {key}"}), 404

        return jsonify({"success": True, "key": key, "value": value})

    except Exception as e:
        logger.error(f"Error getting setting {key}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_api_bp.route("/settings/<key>", methods=["PUT"])
def update_setting(key):
    """
    Update a setting value
    Body: { "value": "...", "encrypt": false }
    """
    try:
        settings_service = current_app.extensions["settings_service"]
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


@settings_api_bp.route("/settings", methods=["POST"])
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
        settings_service = current_app.extensions["settings_service"]
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


@settings_api_bp.route("/settings/<key>", methods=["DELETE"])
def delete_setting(key):
    """Soft delete a setting (set is_active = false)"""
    try:
        settings_service = current_app.extensions["settings_service"]
        success = settings_service.delete_setting(key)

        if success:
            return jsonify({"success": True, "key": key, "message": "Setting deleted successfully"})
        else:
            return jsonify({"success": False, "error": "Setting not found or already deleted"}), 404

    except Exception as e:
        logger.error(f"Error deleting setting {key}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@settings_api_bp.route("/settings/batch", methods=["PUT"])
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
        settings_service = current_app.extensions["settings_service"]
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
