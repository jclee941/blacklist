from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Final

from core.exceptions import BadRequestError
from core.utils.input_security import parse_ip_value


WHITELIST_CREATE_FIELDS: Final = frozenset({"ip_address", "reason", "source", "country"})
BLACKLIST_CREATE_FIELDS: Final = frozenset(
    {
        "ip_address",
        "reason",
        "source",
        "data_source",
        "confidence_level",
        "detection_count",
        "is_active",
        "country",
        "detection_date",
        "removal_date",
    }
)
WHITELIST_UPDATE_FIELDS: Final = frozenset({"reason", "country"})
BLACKLIST_UPDATE_FIELDS: Final = frozenset(
    {"reason", "confidence_level", "is_active", "country", "detection_date", "removal_date"}
)
PayloadValue = str | int | bool | None
Payload = dict[str, PayloadValue]


@dataclass(frozen=True, slots=True)
class WhitelistCreate:
    ip_address: str
    reason: str
    source: str
    country: str | None


@dataclass(frozen=True, slots=True)
class BlacklistCreate:
    ip_address: str
    reason: str
    source: str
    confidence_level: int
    detection_count: int
    is_active: bool
    country: str | None
    detection_date: str | None
    removal_date: str | None


def parse_whitelist_create(data: Payload) -> WhitelistCreate:
    payload = _parse_payload(data, WHITELIST_CREATE_FIELDS)
    return WhitelistCreate(
        ip_address=_required_ip(payload),
        reason=_text(payload, "reason", "VIP Protection"),
        source=_text(payload, "source", "MANUAL"),
        country=_optional_text(payload, "country", 10),
    )


def parse_blacklist_create(data: Payload) -> BlacklistCreate:
    payload = _parse_payload(data, BLACKLIST_CREATE_FIELDS)
    return BlacklistCreate(
        ip_address=_required_ip(payload),
        reason=_text(payload, "reason", "Malicious Activity"),
        source=_text(payload, "source", "MANUAL"),
        confidence_level=_confidence(payload),
        detection_count=_detection_count(payload),
        is_active=_boolean(payload, "is_active", True),
        country=_optional_text(payload, "country", 10),
        detection_date=_optional_date(payload, "detection_date"),
        removal_date=_optional_date(payload, "removal_date"),
    )


def parse_update_payload(data: Payload, list_name: str) -> Payload:
    allowed = WHITELIST_UPDATE_FIELDS if list_name == "whitelist" else BLACKLIST_UPDATE_FIELDS
    payload = _parse_payload(data, allowed)
    if not payload:
        raise BadRequestError("No mutable fields provided", details={"allowed_fields": sorted(allowed)})
    _validate_fields(payload)
    return payload


def _required_ip(payload: Payload) -> str:
    if "ip_address" not in payload:
        raise BadRequestError("ip_address is required", details={"field": "ip_address"})
    return parse_ip_value(payload["ip_address"])


def _text(payload: Payload, field: str, default: str) -> str:
    value = payload.get(field, default)
    if not isinstance(value, str) or not value.strip() or len(value) > 1000:
        raise BadRequestError("Invalid text field", details={"field": field})
    return value.strip()


def _optional_text(payload: Payload, field: str, maximum: int) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise BadRequestError("Invalid text field", details={"field": field})
    return value.strip().upper()


def _confidence(payload: Payload) -> int:
    value = payload.get("confidence_level", 50)
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        raise BadRequestError("Invalid numeric field", details={"field": "confidence_level"})
    return value


def _detection_count(payload: Payload) -> int:
    value = payload.get("detection_count", 1)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 1_000_000:
        raise BadRequestError("Invalid numeric field", details={"field": "detection_count"})
    return value


def _boolean(payload: Payload, field: str, default: bool) -> bool:
    value = payload.get(field, default)
    if not isinstance(value, bool):
        raise BadRequestError("Invalid boolean field", details={"field": field})
    return value


def _optional_date(payload: Payload, field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise BadRequestError("Date must use ISO format", details={"field": field})
    try:
        _ = date.fromisoformat(value)
    except ValueError:
        raise BadRequestError("Date must use ISO format", details={"field": field}) from None
    return value


def _parse_payload(data: Payload, allowed: frozenset[str]) -> Payload:
    if not data:
        raise BadRequestError("A JSON object is required", details={"field": "body"})
    rejected = sorted(set(data) - allowed)
    if rejected:
        raise BadRequestError("Request contains immutable or unsupported fields", details={"fields": rejected})
    return dict(data)


def _validate_fields(payload: Payload) -> None:
    for field in ("reason", "source", "data_source"):
        if field in payload:
            value = payload[field]
            if not isinstance(value, str) or not value.strip() or len(value) > 1000:
                raise BadRequestError("Invalid text field", details={"field": field})
            payload[field] = value.strip()

    if "country" in payload and payload["country"] is not None:
        country = payload["country"]
        if not isinstance(country, str) or not country.strip() or len(country.strip()) > 10:
            raise BadRequestError("Invalid country value", details={"field": "country"})
        payload["country"] = country.strip().upper()

    if "confidence_level" in payload:
        confidence = payload["confidence_level"]
        if isinstance(confidence, bool) or not isinstance(confidence, int) or not 0 <= confidence <= 100:
            raise BadRequestError("Invalid numeric field", details={"field": "confidence_level"})

    if "detection_count" in payload:
        detection_count = payload["detection_count"]
        if isinstance(detection_count, bool) or not isinstance(detection_count, int) or detection_count < 1:
            raise BadRequestError("Invalid numeric field", details={"field": "detection_count"})

    if "is_active" in payload and not isinstance(payload["is_active"], bool):
        raise BadRequestError("is_active must be a boolean", details={"field": "is_active"})

    for field in ("detection_date", "removal_date"):
        if field in payload and payload[field] is not None:
            value = payload[field]
            if not isinstance(value, str):
                raise BadRequestError("Date must use ISO format", details={"field": field})
            try:
                _ = date.fromisoformat(value)
            except ValueError:
                raise BadRequestError("Date must use ISO format", details={"field": field}) from None
