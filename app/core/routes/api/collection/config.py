"""
Collection API Config Operations
Handles collection configuration updates
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, g, current_app
from core.exceptions import BadRequestError, InternalServerError

logger = logging.getLogger(__name__)

collection_config_bp = Blueprint("collection_config", __name__)


@collection_config_bp.route("/collection/config/update", methods=["POST"])
def update_collection_config():
    """
    Update collection configuration
    """
    data = request.get_json() or {}

    # Validate request body
    if not data:
        raise BadRequestError(message="No configuration data provided", details={"parameter": "body"})

    try:
        settings_service = current_app.extensions["settings_service"]

        updated_keys = []
        failed_keys = []

        # Update each configuration key
        for key, value in data.items():
            # Prefix keys with 'collection_' for categorization
            setting_key = f"collection_{key}"

            try:
                success = settings_service.set_setting(setting_key, value)
                if success:
                    updated_keys.append(key)
                    logger.info(f"Updated collection config: {key}={value}")
                else:
                    failed_keys.append(key)
                    logger.warning(f"Failed to update collection config: {key}")
            except Exception as e:
                failed_keys.append(key)
                logger.error(f"Error updating collection config {key}: {e}", exc_info=True)

        # Return response based on results
        if len(failed_keys) == 0:
            # Full success
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "message": "Collection configuration updated successfully",
                        "updated": updated_keys,
                        "failed": [],
                    },
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.request_id,
                }
            ), 200
        elif len(updated_keys) > 0:
            # Partial success - raise error with details
            raise InternalServerError(
                message="Collection configuration partially updated",
                details={"updated": updated_keys, "failed": failed_keys},
            )
        else:
            # Total failure
            raise InternalServerError(
                message="Failed to update collection configuration",
                details={"failed": failed_keys},
            )

    except BadRequestError:
        raise  # Re-raise validation errors
    except InternalServerError:
        raise  # Re-raise partial/total failure errors
    except Exception as e:
        logger.error(f"Collection config update error: {e}", exc_info=True)
        raise InternalServerError(
            message="Unexpected error updating collection configuration",
            details={"error_type": type(e).__name__},
        )
