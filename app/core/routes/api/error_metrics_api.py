"""
Error Metrics API
에러 통계 및 모니터링 API (system_api.py에서 분리)

Created: 2026-01-05 (Technical Debt Resolution)
"""

from ..api_routes import api_bp
from flask import request
import logging
from ...exceptions import (
    ValidationError,
    InternalServerError,
)

logger = logging.getLogger(__name__)


@api_bp.route("/monitoring/errors/stats", methods=["GET"])
def get_error_statistics():
    try:
        from core.monitoring import error_metrics
        from core.utils.response_utils import success_response

        stats = error_metrics.get_statistics()
        return success_response(stats)

    except Exception as e:
        logger.error(f"Error statistics retrieval failed: {e}", exc_info=True)
        raise InternalServerError(
            message="Failed to retrieve error statistics",
        )


@api_bp.route("/monitoring/errors/recent", methods=["GET"])
def get_recent_errors():
    try:
        from core.monitoring import error_metrics
        from core.utils.response_utils import success_response

        try:
            limit = int(request.args.get("limit", 50))
        except ValueError:
            raise ValidationError(message="Limit must be a valid integer", field="limit")

        if limit < 1 or limit > 200:
            raise ValidationError(
                message="Limit must be between 1 and 200",
                field="limit",
                details={"provided_value": limit, "allowed_range": "1-200"},
            )

        exception_type = request.args.get("type")
        endpoint = request.args.get("endpoint")

        errors = error_metrics.get_recent_errors(limit=limit, exception_type=exception_type, endpoint=endpoint)

        data = {
            "errors": errors,
            "total_shown": len(errors),
            "filters_applied": {
                "limit": limit,
                "type": exception_type,
                "endpoint": endpoint,
            },
        }

        return success_response(data)

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Recent errors retrieval failed: {e}", exc_info=True)
        raise InternalServerError(
            message="Failed to retrieve recent errors",
        )


@api_bp.route("/monitoring/errors/trends", methods=["GET"])
def get_error_trends():
    try:
        from core.monitoring import error_metrics
        from core.utils.response_utils import success_response

        try:
            window_minutes = int(request.args.get("window", 60))
            bucket_minutes = int(request.args.get("bucket", 5))
        except ValueError:
            raise ValidationError(
                message="Window and bucket must be valid integers",
                field="window/bucket",
            )

        if window_minutes < 5 or window_minutes > 1440:
            raise ValidationError(
                message="Window must be between 5 and 1440 minutes",
                field="window",
                details={"provided_value": window_minutes, "allowed_range": "5-1440"},
            )

        if bucket_minutes < 1 or bucket_minutes > window_minutes:
            raise ValidationError(
                message="Bucket must be between 1 and window minutes",
                field="bucket",
                details={
                    "provided_value": bucket_minutes,
                    "allowed_range": f"1-{window_minutes}",
                },
            )

        trends = error_metrics.get_error_trends(window_minutes=window_minutes, bucket_minutes=bucket_minutes)

        return success_response(
            {
                "trends": trends,
                "window_minutes": window_minutes,
                "bucket_minutes": bucket_minutes,
            }
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error trends retrieval failed: {e}", exc_info=True)
        raise InternalServerError(
            message="Failed to retrieve error trends",
        )


@api_bp.route("/monitoring/errors/top", methods=["GET"])
def get_top_errors():
    try:
        from core.monitoring import error_metrics
        from core.utils.response_utils import success_response

        by = request.args.get("by", "type")
        valid_by = ["type", "endpoint", "status_code"]

        if by not in valid_by:
            raise ValidationError(
                message=f"Invalid 'by' parameter: {by}",
                field="by",
                details={"provided_value": by, "allowed_values": valid_by},
            )

        try:
            limit = int(request.args.get("limit", 10))
        except ValueError:
            raise ValidationError(message="Limit must be a valid integer", field="limit")

        if limit < 1 or limit > 50:
            raise ValidationError(
                message="Limit must be between 1 and 50",
                field="limit",
                details={"provided_value": limit, "allowed_range": "1-50"},
            )

        top_errors = error_metrics.get_top_errors(by=by, limit=limit)

        data = {"top_errors": top_errors, "grouped_by": by, "limit": limit}

        return success_response(data)

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Top errors retrieval failed: {e}", exc_info=True)
        raise InternalServerError(
            message="Failed to retrieve top errors",
        )
