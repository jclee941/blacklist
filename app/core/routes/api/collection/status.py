"""
Collection API Status Operations
Handles collection status and health checks
"""

import logging
from datetime import datetime
from typing import TypedDict
from flask import Blueprint, jsonify, g, current_app
from core.exceptions import ServiceUnavailableError, ExternalAPIError
from .utils import call_collector_api

logger = logging.getLogger(__name__)

collection_status_bp = Blueprint("collection_status", __name__)


class CollectorState(TypedDict, total=False):
    enabled: bool
    last_run: str | None
    interval_seconds: int


def _check_if_actively_collecting(collectors: dict[str, CollectorState]) -> bool:
    from datetime import timedelta

    now = datetime.now()
    for name, info in collectors.items():
        if not info.get("enabled"):
            continue
        last_run_str = info.get("last_run")
        if not last_run_str:
            continue
        try:
            last_run = datetime.fromisoformat(last_run_str)
            interval = info.get("interval_seconds", 3600)
            if now - last_run < timedelta(seconds=min(interval, 300)):
                return True
        except (ValueError, TypeError):
            continue
    return False


@collection_status_bp.route("/status", methods=["GET"])
def get_collection_status():
    """
    Get overall collection status for all sources
    """
    health = call_collector_api("/status")

    # Check if API call failed (connection error)
    if health.get("success") is False:
        error_msg = health.get("error", "Unknown error")
        if "Cannot connect" in error_msg:
            raise ServiceUnavailableError(
                message=error_msg,
                service_name="Collector",
            )
        else:
            raise ExternalAPIError(
                message=error_msg,
                api_name="Collector",
            )

    # Check if collector responded successfully
    if health.get("status") == "healthy":
        collectors = health.get("collectors", {})
        is_collecting = _check_if_actively_collecting(collectors)

        return jsonify(
            {
                "success": True,
                "data": {
                    "is_running": is_collecting,
                    "collectors": collectors,
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        )
    else:
        # Unexpected response format - graceful degradation
        logger.warning(f"Unexpected collector response format: {health}")
        return jsonify(
            {
                "success": True,
                "data": {"is_running": False, "collectors": {}},
                "message": "Scheduler is running but status details unavailable",
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        )


@collection_status_bp.route("/health", methods=["GET"])
def collection_health():
    """
    Health check for collection system
    """
    try:
        # Use dependency injection via app.extensions
        db_service = current_app.extensions["db_service"]

        # Check collector service
        collector_health = call_collector_api("/health")
        collector_status = collector_health.get("status", "unhealthy")

        # Check database
        db_healthy = db_service.health_check()
        db_status = "healthy" if db_healthy else "unhealthy"

        # Overall status
        overall_status = "healthy" if (collector_status == "healthy" and db_status == "healthy") else "unhealthy"

        return jsonify(
            {
                "success": True,
                "status": overall_status,  # Top-level status for backward compatibility
                "data": {
                    "status": overall_status,
                    "collector_service": collector_status,
                    "database": db_status,
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error checking collection health: {e}", exc_info=True)
        # Graceful degradation - always return 200 with unhealthy status
        return jsonify(
            {
                "success": True,
                "data": {"status": "unhealthy"},
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200
