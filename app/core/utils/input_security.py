from __future__ import annotations

from ipaddress import ip_address
from typing import Final

from core.exceptions import APIError, BadRequestError


MAX_BATCH_ITEMS: Final = 1000
InputScalar = str | int | bool | None


def parse_ip_value(value: InputScalar) -> str:
    if not isinstance(value, str):
        raise BadRequestError("IP address must be a string", details={"field": "ip_address"})
    normalized = value.strip()
    try:
        return str(ip_address(normalized))
    except ValueError:
        raise BadRequestError("Invalid IP address format", details={"field": "ip_address"}) from None


def parse_ip_batch(value: list[str] | InputScalar) -> list[str]:
    if not isinstance(value, list) or not value:
        raise BadRequestError("IPs list is required", details={"field": "ips"})
    if len(value) > MAX_BATCH_ITEMS:
        raise APIError(
            "Batch request exceeds the maximum item count",
            status_code=413,
            error_code="BATCH_TOO_LARGE",
            details={"maximum": MAX_BATCH_ITEMS},
        )
    return [parse_ip_value(item) for item in value]
