"""REGTECH 관리자 수집 트리거 라우트."""

import logging
from datetime import datetime, timedelta

from flask import current_app, jsonify, request

logger = logging.getLogger(__name__)


def register_admin_collection_routes(bp):
    @bp.route("/regtech/collect", methods=["POST"])
    def trigger_regtech_collection():
        """
        Trigger REGTECH collection manually.
        Body: {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"} (optional)
        """
        try:
            collection_service = current_app.extensions["collection_service"]
            data = request.get_json() or {}
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            logger.info(f"REGTECH collection trigger requested: {start_date} to {end_date}")
            result = collection_service.trigger_regtech_collection(
                start_date=start_date,
                end_date=end_date,
            )

            if result.get("success"):
                logger.info(f"✅ REGTECH collection completed: {result.get('collected_count', 0)} items")
                return jsonify(
                    {
                        "success": True,
                        "message": "REGTECH collection triggered successfully",
                        "collected_count": result.get("collected_count", 0),
                        "start_date": start_date,
                        "end_date": end_date,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            logger.warning(f"REGTECH collection failed: {result.get('error', 'Unknown error')}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result.get("error", "Collection failed"),
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )
        except Exception as exc:
            logger.error(f"REGTECH collection trigger error: {exc}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": str(exc),
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )
