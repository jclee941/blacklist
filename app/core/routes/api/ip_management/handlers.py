from datetime import datetime
from typing import Any, Optional

from flask import g

from ....exceptions import ValidationError


def validate_pagination(page: Any, limit: Any) -> tuple[int, int]:
    try:
        page = int(page) if page is not None else 1
        limit = int(limit) if limit is not None else 50
    except ValueError:
        raise ValidationError(
            message="Page and limit must be valid integers",
            field="page/limit",
        )

    if page < 1:
        raise ValidationError(
            message="Page number must be >= 1",
            field="page",
            details={"provided_value": page},
        )
    if limit < 1 or limit > 1000:
        raise ValidationError(
            message="Limit must be between 1 and 1000",
            field="limit",
            details={"provided_value": limit, "allowed_range": "1-1000"},
        )

    return page, limit


def validate_list_type(list_type: Optional[str]) -> Optional[str]:
    if list_type and list_type not in ("whitelist", "blacklist"):
        raise ValidationError(
            message=f"Invalid type: {list_type}. Must be 'whitelist' or 'blacklist'",
            field="type",
            details={
                "provided_value": list_type,
                "allowed_values": ["whitelist", "blacklist"],
            },
        )
    return list_type


def parse_bool_param(value: Optional[str], default: Optional[bool] = None) -> Optional[bool]:
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes")


def paginated_response(
    items: list[dict],
    total: int,
    page: int,
    limit: int,
) -> dict:
    return {
        "success": True,
        "data": {
            "items": items,
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit if limit > 0 else 0,
            },
        },
        "timestamp": datetime.now().isoformat(),
        "request_id": g.request_id,
    }


def success_response(data: Any, status_code: int = 200) -> tuple[dict, int]:
    return {
        "success": True,
        "data": data,
        "timestamp": datetime.now().isoformat(),
        "request_id": g.request_id,
    }, status_code


def deleted_response(deleted_ip: str) -> tuple[dict, int]:
    return success_response({"deleted_ip": deleted_ip}, 200)
