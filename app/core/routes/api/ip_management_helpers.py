"""
IP Management API Helpers
Extracted helper functions for reducing code duplication in ip_management_api.py

Created: 2026-01-05 (Technical Debt Resolution)
"""

from datetime import datetime
from typing import Any, List, Dict, Tuple
from flask import request, jsonify, g, Response
from ...exceptions import ValidationError


def parse_pagination_params(default_page: int = 1, default_limit: int = 50) -> Tuple[int, int]:
    """
    Parse and validate pagination parameters from request args.

    Args:
        default_page: Default page number
        default_limit: Default items per page

    Returns:
        Tuple of (page, limit)

    Raises:
        ValidationError: If parameters are not valid integers
    """
    try:
        page = int(request.args.get("page", default_page))
        limit = int(request.args.get("limit", default_limit))
    except ValueError as e:
        raise ValidationError(
            message="Page and limit must be valid integers",
            field="page/limit",
            details={"error": str(e)},
        )
    return page, limit


def validate_pagination(page: int, limit: int, max_limit: int = 1000) -> None:
    """
    Validate pagination parameter ranges.

    Args:
        page: Page number
        limit: Items per page
        max_limit: Maximum allowed limit

    Raises:
        ValidationError: If parameters are out of valid range
    """
    if page < 1:
        raise ValidationError(
            message="Page number must be >= 1",
            field="page",
            details={"provided_value": page},
        )
    if limit < 1 or limit > max_limit:
        raise ValidationError(
            message=f"Limit must be between 1 and {max_limit}",
            field="limit",
            details={"provided_value": limit, "allowed_range": f"1-{max_limit}"},
        )


def serialize_rows(data: List[Any]) -> List[Dict[str, Any]]:
    """
    Serialize database rows, converting datetime fields to ISO format.

    Args:
        data: List of database row objects (RealDictRow or similar)

    Returns:
        List of dictionaries with datetime fields converted to ISO strings
    """
    serialized_data = []
    for row in data:
        row_dict = dict(row)
        for key, value in row_dict.items():
            if isinstance(value, datetime):
                row_dict[key] = value.isoformat()
        serialized_data.append(row_dict)
    return serialized_data


def serialize_single_row(row: Any) -> Dict[str, Any]:
    """
    Serialize a single database row, converting datetime fields to ISO format.

    Args:
        row: Database row object (RealDictRow or similar)

    Returns:
        Dictionary with datetime fields converted to ISO strings
    """
    row_dict = dict(row)
    for key, value in row_dict.items():
        if isinstance(value, datetime):
            row_dict[key] = value.isoformat()
    return row_dict


def paginated_response(items: List[Dict[str, Any]], total: int, page: int, limit: int) -> Tuple[Response, int]:
    """
    Create a standardized paginated JSON response.

    Args:
        items: List of serialized items
        total: Total count of items
        page: Current page number
        limit: Items per page

    Returns:
        Tuple of (Flask Response, HTTP status code)
    """
    return jsonify(
        {
            "success": True,
            "data": {
                "items": items,
                "pagination": {
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "total_pages": (total + limit - 1) // limit,
                },
            },
            "timestamp": datetime.now().isoformat(),
            "request_id": g.request_id,
        }
    ), 200


def success_response(data: Dict[str, Any]) -> Tuple[Response, int]:
    """
    Create a standardized success JSON response for single item operations.

    Args:
        data: The data to include in the response

    Returns:
        Tuple of (Flask Response, HTTP status code)
    """
    return jsonify(
        {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "request_id": g.request_id,
        }
    ), 200


def created_response(data: Dict[str, Any]) -> Tuple[Response, int]:
    """
    Create a standardized success JSON response for create operations.

    Args:
        data: The created item data

    Returns:
        Tuple of (Flask Response, HTTP status code 201)
    """
    return jsonify(
        {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "request_id": g.request_id,
        }
    ), 201


def deleted_response(item_id: int, item_type: str = "item") -> Tuple[Response, int]:
    """
    Create a standardized success JSON response for delete operations.

    Args:
        item_id: ID of the deleted item
        item_type: Type of the deleted item (for message)

    Returns:
        Tuple of (Flask Response, HTTP status code)
    """
    return jsonify(
        {
            "success": True,
            "message": f"{item_type.capitalize()} deleted successfully",
            "data": {"deleted_id": item_id},
            "timestamp": datetime.now().isoformat(),
            "request_id": g.request_id,
        }
    ), 200
