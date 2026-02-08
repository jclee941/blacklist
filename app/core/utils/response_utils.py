"""
Response Utility Functions
Standardized response formatting for API endpoints

Created: 2025-11-21 (Error Handling Standardization - HIGH PRIORITY #4)
Reference: docs/104-ERROR-HANDLING-STANDARDIZATION-PLAN.md
"""

from flask import jsonify, request
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


def success_response(data: Any, status_code: int = 200, message: Optional[str] = None) -> Tuple[Any, int]:
    """
    Create standardized success response.

    Args:
        data: Response data (will be nested under "data" key)
        status_code: HTTP status code (default: 200)
        message: Optional message to include in data

    Returns:
        Tuple of (jsonify response, status_code)

    Example:
        return success_response({"total": 100, "items": [...]})
        # Returns: ({"success": True, "data": {...}, "timestamp": "...", "request_id": "..."}, 200)
    """
    response_data = {
        "success": True,
        "data": data,
        "timestamp": datetime.now().isoformat(),
        "request_id": getattr(request, "id", None),
    }

    # Add optional message to data if provided
    if message and isinstance(data, dict):
        response_data["data"]["message"] = message

    return jsonify(response_data), status_code


def paginated_response(
    items: list,
    total: int,
    page: int,
    limit: int,
    status_code: int = 200,
    additional_data: Optional[Dict[str, Any]] = None,
) -> Tuple[Any, int]:
    """
    Create standardized paginated response.

    Args:
        items: List of items for current page
        total: Total number of items across all pages
        page: Current page number
        limit: Items per page
        status_code: HTTP status code (default: 200)
        additional_data: Optional additional data to include

    Returns:
        Tuple of (jsonify response, status_code)

    Example:
        return paginated_response(
            items=[...],
            total=1000,
            page=1,
            limit=50,
            additional_data={"source": "regtech"}
        )
    """
    data = {
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 0,
        },
    }

    # Merge additional data if provided
    if additional_data:
        data.update(additional_data)

    return success_response(data, status_code)


def empty_response(message: str = "No content", status_code: int = 204) -> Tuple[Any, int]:
    """
    Create standardized empty response (typically 204 No Content).

    Args:
        message: Optional message (not included in 204 responses)
        status_code: HTTP status code (default: 204)

    Returns:
        Tuple of (empty response, status_code)

    Example:
        return empty_response()
        # Returns: ('', 204)
    """
    if status_code == 204:
        return "", 204
    else:
        return success_response({"message": message}, status_code)


def created_response(data: Any, location: Optional[str] = None) -> Tuple[Any, int]:
    """
    Create standardized 201 Created response.

    Args:
        data: Created resource data
        location: Optional Location header URL

    Returns:
        Tuple of (jsonify response, 201)

    Example:
        return created_response(
            {"id": 123, "name": "New Item"},
            location="/api/items/123"
        )
    """
    response = success_response(data, 201)

    if location:
        response[0].headers["Location"] = location

    return response


def deleted_response(
    message: str = "Resource deleted successfully", deleted_count: Optional[int] = None
) -> Tuple[Any, int]:
    """
    Create standardized delete response.

    Args:
        message: Success message
        deleted_count: Optional count of deleted items

    Returns:
        Tuple of (jsonify response, 200)

    Example:
        return deleted_response(
            message="IP addresses deleted",
            deleted_count=5
        )
    """
    data = {"message": message}
    if deleted_count is not None:
        data["deleted_count"] = deleted_count

    return success_response(data, 200)


def health_response(status: str = "healthy", checks: Optional[Dict[str, Any]] = None) -> Tuple[Any, int]:
    """
    Create standardized health check response.
    Uses graceful degradation - always returns 200 with status field.

    Args:
        status: Health status ("healthy" or "unhealthy")
        checks: Optional dict of individual health checks

    Returns:
        Tuple of (jsonify response, 200)

    Example:
        return health_response(
            status="healthy",
            checks={
                "database": True,
                "cache": True,
                "total_ips": 1234
            }
        )
    """
    data = {"status": status}
    if checks:
        data.update(checks)

    return success_response(data, 200)


def batch_operation_response(
    total: int, successful: int, failed: int, errors: Optional[list] = None, status_code: int = 200
) -> Tuple[Any, int]:
    """
    Create standardized batch operation response.

    Args:
        total: Total items processed
        successful: Number of successful operations
        failed: Number of failed operations
        errors: Optional list of error details
        status_code: HTTP status code (default: 200)

    Returns:
        Tuple of (jsonify response, status_code)

    Example:
        return batch_operation_response(
            total=100,
            successful=95,
            failed=5,
            errors=[{"item": "192.168.1.1", "reason": "Invalid format"}]
        )
    """
    data = {
        "total": total,
        "successful": successful,
        "failed": failed,
        "success_rate": round((successful / total * 100) if total > 0 else 0, 2),
    }

    if errors:
        data["errors"] = errors

    return success_response(data, status_code)


def statistics_response(stats: Dict[str, Any], period: Optional[str] = None, status_code: int = 200) -> Tuple[Any, int]:
    """
    Create standardized statistics response.

    Args:
        stats: Statistics data
        period: Optional time period (e.g., "last_24h", "last_7d")
        status_code: HTTP status code (default: 200)

    Returns:
        Tuple of (jsonify response, status_code)

    Example:
        return statistics_response(
            stats={"total": 1234, "active": 1000},
            period="last_24h"
        )
    """
    data = {"statistics": stats}
    if period:
        data["period"] = period

    return success_response(data, status_code)


def collection_response(
    source: str, items_collected: int, success: bool = True, errors: Optional[list] = None
) -> Tuple[Any, int]:
    """
    Create standardized collection operation response.

    Args:
        source: Collection source name
        items_collected: Number of items collected
        success: Whether collection was successful
        errors: Optional list of collection errors

    Returns:
        Tuple of (jsonify response, 200)

    Example:
        return collection_response(
            source="regtech",
            items_collected=150,
            success=True
        )
    """
    data = {
        "source": source,
        "items_collected": items_collected,
        "success": success,
        "collection_timestamp": datetime.now().isoformat(),
    }

    if errors:
        data["errors"] = errors

    return success_response(data, 200)
