"""
Collection API Trigger Operations
Handles manual collection triggering
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, g
from ....exceptions import ValidationError, ServiceUnavailableError, ExternalAPIError
from .utils import call_collector_api

logger = logging.getLogger(__name__)

collection_trigger_bp = Blueprint("collection_trigger", __name__)


@collection_trigger_bp.route("/trigger/<source>", methods=["POST"])
def trigger_collection(source: str):
    """
    Trigger manual collection for specific source
    """
    source_upper = source.upper()

    # Validate source parameter
    if source_upper not in ["REGTECH", "ALL"]:
        raise ValidationError(
            message=f"Invalid source: {source}. Only 'regtech' or 'all' is supported",
            field="source",
            details={
                "provided_value": source,
                "allowed_values": ["regtech", "all"],
            },
        )

    data = request.get_json() or {}
    force = data.get("force", False)

    logger.info(f"Triggering collection for {source_upper} (force={force})")

    # Call collector service to trigger collection
    result = call_collector_api(f"/api/force-collection/{source_upper}", method="POST", data={"force": force})

    # Check if API call failed
    if result.get("success") is False:
        error_msg = result.get("error", "Unknown error")
        if "Cannot connect" in error_msg:
            raise ServiceUnavailableError(
                message="Collector service unavailable",
                service_name="Collector",
            )
        else:
            logger.error(f"❌ {source_upper} collection trigger failed: {error_msg}")
            raise ExternalAPIError(
                message=f"Collection trigger failed: {error_msg}",
                api_name="Collector",
                details={"source": source_upper, "force": force},
            )

    # Success - return standardized response
    logger.info(f"✅ {source_upper} collection triggered successfully")
    return jsonify(
        {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat(),
            "request_id": g.request_id,
        }
    )
