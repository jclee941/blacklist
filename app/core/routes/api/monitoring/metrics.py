"""
Metrics API routes
Provides access to application performance metrics

Created: 2025-11-21 (Cache Metrics Integration - MEDIUM PRIORITY #8)
Reference: docs/108-REDIS-CACHING-IMPLEMENTATION.md
"""

import logging
from flask import jsonify, request
from . import monitoring_bp

logger = logging.getLogger(__name__)

# Import metrics collectors
try:
    from core.monitoring.cache_metrics import cache_metrics

    CACHE_METRICS_ENABLED = True
except ImportError:
    logger.warning("Cache metrics not available")
    CACHE_METRICS_ENABLED = False

try:
    from core.monitoring.error_metrics import error_metrics

    ERROR_METRICS_ENABLED = True
except ImportError:
    logger.warning("Error metrics not available")
    ERROR_METRICS_ENABLED = False


@monitoring_bp.route("/monitoring/cache/stats", methods=["GET"])
def get_cache_stats():
    """
    Get aggregated cache statistics

    Returns comprehensive cache performance metrics including:
    - Hit/miss counts and rates
    - Latency statistics
    - Per-endpoint breakdowns
    - Cache key prefix statistics

    ---
    Example Response:
    {
        "success": true,
        "data": {
            "total_operations": 10000,
            "cache_hits": 9500,
            "cache_misses": 500,
            "hit_rate": 95.0,
            "avg_hit_latency_ms": 2.5,
            "avg_miss_latency_ms": 3.2,
            "by_endpoint": {
                "/api/stats": {"hits": 1000, "misses": 50, "hit_rate": 95.24}
            },
            "by_prefix": {
                "stats": {"hits": 9000, "misses": 450, "hit_rate": 95.24}
            },
            "uptime_hours": 24.5
        }
    }
    """
    if not CACHE_METRICS_ENABLED:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "METRICS_UNAVAILABLE",
                    "message": "Cache metrics collection is not enabled",
                },
            }
        ), 503

    try:
        stats = cache_metrics.get_statistics()
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        logger.exception("Failed to retrieve cache statistics")
        return jsonify({"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@monitoring_bp.route("/monitoring/cache/operations", methods=["GET"])
def get_cache_operations():
    """
    Get recent cache operations

    Query Parameters:
    - limit (int): Maximum number of operations to return (default: 50, max: 500)
    - operation_type (str): Filter by operation type ('hit', 'miss', 'set', 'delete')
    - endpoint (str): Filter by API endpoint

    ---
    Example Response:
    {
        "success": true,
        "data": [
            {
                "timestamp": "2025-11-21T10:30:00.000Z",
                "operation": "hit",
                "cache_key": "stats:get_statistics::",
                "endpoint": "/api/stats",
                "latency_ms": 2.3
            }
        ]
    }
    """
    if not CACHE_METRICS_ENABLED:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "METRICS_UNAVAILABLE",
                    "message": "Cache metrics collection is not enabled",
                },
            }
        ), 503

    try:
        # Parse query parameters
        limit = request.args.get("limit", 50, type=int)
        limit = min(limit, 500)  # Cap at 500

        operation_type = request.args.get("operation_type", None, type=str)
        endpoint = request.args.get("endpoint", None, type=str)

        operations = cache_metrics.get_recent_operations(limit=limit, operation_type=operation_type, endpoint=endpoint)

        return jsonify(
            {
                "success": True,
                "data": operations,
                "count": len(operations),
                "filters": {
                    "limit": limit,
                    "operation_type": operation_type,
                    "endpoint": endpoint,
                },
            }
        )
    except Exception as e:
        logger.exception("Failed to retrieve cache operations")
        return jsonify({"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@monitoring_bp.route("/monitoring/cache/trends", methods=["GET"])
def get_cache_trends():
    """
    Get cache performance trends over time

    Query Parameters:
    - window_minutes (int): Time window in minutes (default: 60, max: 1440 = 24 hours)
    - bucket_minutes (int): Time bucket size in minutes (default: 5)

    ---
    Example Response:
    {
        "success": true,
        "data": {
            "buckets": [
                {
                    "start": "2025-11-21T10:00:00.000Z",
                    "end": "2025-11-21T10:05:00.000Z",
                    "hits": 500,
                    "misses": 25,
                    "hit_rate": 95.24
                }
            ],
            "total_in_window": 10000,
            "window_minutes": 60,
            "bucket_minutes": 5
        }
    }
    """
    if not CACHE_METRICS_ENABLED:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "METRICS_UNAVAILABLE",
                    "message": "Cache metrics collection is not enabled",
                },
            }
        ), 503

    try:
        # Parse query parameters
        window_minutes = request.args.get("window_minutes", 60, type=int)
        window_minutes = min(window_minutes, 1440)  # Cap at 24 hours

        bucket_minutes = request.args.get("bucket_minutes", 5, type=int)
        bucket_minutes = max(bucket_minutes, 1)  # Minimum 1 minute

        trends = cache_metrics.get_cache_trends(window_minutes=window_minutes, bucket_minutes=bucket_minutes)

        return jsonify({"success": True, "data": trends})
    except Exception as e:
        logger.exception("Failed to retrieve cache trends")
        return jsonify({"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@monitoring_bp.route("/monitoring/cache/top-keys", methods=["GET"])
def get_top_cache_keys():
    """
    Get top cache keys by hits or misses

    Query Parameters:
    - by (str): Sort by 'hits' or 'misses' (default: 'hits')
    - limit (int): Number of top keys to return (default: 10, max: 50)

    ---
    Example Response:
    {
        "success": true,
        "data": [
            {"prefix": "stats", "count": 9500},
            {"prefix": "blacklist", "count": 450}
        ]
    }
    """
    if not CACHE_METRICS_ENABLED:
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "METRICS_UNAVAILABLE",
                    "message": "Cache metrics collection is not enabled",
                },
            }
        ), 503

    try:
        # Parse query parameters
        by = request.args.get("by", "hits", type=str)
        if by not in ("hits", "misses"):
            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "INVALID_PARAMETER",
                        "message": "Parameter 'by' must be 'hits' or 'misses'",
                    },
                }
            ), 400

        limit = request.args.get("limit", 10, type=int)
        limit = min(limit, 50)  # Cap at 50

        top_keys = cache_metrics.get_top_keys(by=by, limit=limit)

        return jsonify({"success": True, "data": top_keys, "sorted_by": by, "limit": limit})
    except Exception as e:
        logger.exception("Failed to retrieve top cache keys")
        return jsonify({"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@monitoring_bp.route("/monitoring/metrics", methods=["GET"])
def get_all_metrics():
    """
    Get all available metrics (cache + error metrics)

    Returns:
    {
        "success": true,
        "data": {
            "cache": {...},
            "errors": {...}
        }
    }
    """
    result = {"success": True, "data": {}}

    # Add cache metrics
    if CACHE_METRICS_ENABLED:
        try:
            result["data"]["cache"] = cache_metrics.get_statistics()
        except Exception as e:
            logger.error(f"Failed to retrieve cache metrics: {e}")
            result["data"]["cache"] = {"error": str(e)}

    # Add error metrics
    if ERROR_METRICS_ENABLED:
        try:
            result["data"]["errors"] = error_metrics.get_statistics()
        except Exception as e:
            logger.error(f"Failed to retrieve error metrics: {e}")
            result["data"]["errors"] = {"error": str(e)}

    return jsonify(result)
