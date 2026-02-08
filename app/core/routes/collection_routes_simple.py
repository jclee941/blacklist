"""
Simple Collection Routes
Collection trigger and config endpoints at /collection/*
"""

from flask import Blueprint, request, jsonify, current_app
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Create Blueprint with /collection prefix
collection_simple_bp = Blueprint("collection_simple", __name__, url_prefix="/collection")


@collection_simple_bp.route("/trigger", methods=["POST"])
def trigger_collection():
    """
    Trigger manual collection
    Body: {"source": "regtech" | "all", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"} (optional)
    """
    try:
        # Use dependency injection via app.extensions
        collection_service = current_app.extensions["collection_service"]

        data = request.get_json() or {}
        source = data.get("source", "all")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        # Default to last 7 days if no dates provided
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        logger.info(f"Collection trigger requested: source={source}, dates={start_date} to {end_date}")

        # Trigger collection based on source
        if source.lower() == "regtech":
            result = collection_service.trigger_regtech_collection(start_date=start_date, end_date=end_date)
        elif source.lower() == "all":
            result = collection_service.trigger_all_collections()
        else:
            # Fallback to generic collection
            result = collection_service.trigger_collection(source)

        if result.get("success"):
            logger.info(f"✅ Collection completed: {result.get('collected_count', 0)} items")
            return jsonify(
                {
                    "success": True,
                    "message": "Collection triggered successfully",
                    "collected_count": result.get("collected_count", 0),
                    "source": source,
                    "start_date": start_date,
                    "end_date": end_date,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            logger.warning(f"Collection failed: {result.get('error', 'Unknown error')}")
            return jsonify(
                {
                    "success": False,
                    "error": result.get("error", "Collection failed"),
                    "source": source,
                    "timestamp": datetime.now().isoformat(),
                }
            ), 500

    except Exception as e:
        logger.error(f"Collection trigger error: {e}")
        return jsonify({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}), 500
