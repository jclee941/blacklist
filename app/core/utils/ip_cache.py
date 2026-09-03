from __future__ import annotations

from collections.abc import Iterable

from flask import current_app


def invalidate_ip_caches(ip_addresses: Iterable[str]) -> None:
    blacklist_service = current_app.extensions.get("blacklist_service")
    redis_client = getattr(blacklist_service, "redis_client", None)
    if redis_client is None:
        return
    keys = tuple(key for ip in dict.fromkeys(ip_addresses) for key in (f"blacklist:{ip}", f"whitelist:{ip}"))
    if keys:
        redis_client.delete(*keys)
