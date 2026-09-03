"""Fortinet feed authentication and source-network policy."""

from __future__ import annotations

import secrets
from functools import wraps
from ipaddress import ip_address, ip_network

from flask import current_app, jsonify, request


def feed_access_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        expected = current_app.config.get("FORTINET_FEED_TOKEN", "")
        networks = current_app.config.get("FORTINET_FEED_ALLOWED_NETWORKS", ())
        if not expected or not networks:
            return _error("FEED_POLICY_UNAVAILABLE", "Feed access policy is not configured", 503)

        header = request.headers.get("Authorization", "")
        supplied = header[7:] if header.startswith("Bearer ") else ""
        if not secrets.compare_digest(supplied.encode(), expected.encode()):
            return _error("FEED_TOKEN_INVALID", "A valid feed bearer token is required", 401)

        try:
            client = ip_address(request.remote_addr or "")
            allowed = any(client in ip_network(network, strict=False) for network in networks)
        except ValueError:
            allowed = False
        if not allowed:
            return _error("FEED_SOURCE_FORBIDDEN", "Feed source is not allowed", 403)
        return view(*args, **kwargs)

    return wrapped


def _error(code: str, detail: str, status: int):
    return jsonify(
        {"type": "about:blank", "title": "Feed Access Error", "status": status, "detail": detail, "code": code}
    ), status
