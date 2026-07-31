from __future__ import annotations

import logging
from typing import Any, Dict

from .dependencies import db_service

logger = logging.getLogger(f"{__package__}.operations")


def load_initial_stats(collection_stats: Dict[str, Any], database: Any = db_service) -> None:
    try:
        stats = database.get_collection_stats()
        if not stats:
            return

        if stats.get("latest_collection"):
            last_collection = stats["latest_collection"]
            last_value = last_collection.isoformat() if hasattr(last_collection, "isoformat") else str(last_collection)
            collection_stats["last_run"] = last_value
            collection_stats["last_success"] = last_value
            logger.info("📅 Loaded last collection time from DB: %s", last_value)

        if stats.get("total_collections"):
            collection_stats["total_runs"] = stats["total_collections"]
        if stats.get("successful_collections"):
            collection_stats["successful_runs"] = stats["successful_collections"]
        if stats.get("failed_collections"):
            collection_stats["failed_runs"] = stats["failed_collections"]

        logger.info(
            "📊 Loaded run counts from DB: total=%s, success=%s, failed=%s",
            collection_stats["total_runs"],
            collection_stats["successful_runs"],
            collection_stats["failed_runs"],
        )
    except Exception as exc:
        logger.warning("⚠️ Could not load initial stats from DB: %s", exc)
