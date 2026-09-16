"""
Fortinet API Utilities
Shared helper functions for Fortinet routes
"""

import logging
from flask import request, current_app

logger = logging.getLogger(__name__)


def _log_pull_request(endpoint: str, ip_count: int, status_code: int = 200, response_time_ms: int = 0):
    """Log FortiGate pull request to database"""
    try:
        db_service = current_app.extensions.get("db_service")
        if not db_service:
            return

        # TrustedProxyMiddleware removes X-Forwarded-For from the environment after
        # resolving exactly one trusted hop, so remote_addr is the client address.
        client_ip = request.remote_addr

        user_agent = request.headers.get("User-Agent", "")[:500]  # Limit length

        db_service.execute(
            """
            INSERT INTO fortinet_pull_logs
            (device_ip, user_agent, request_path, ip_count, response_time_ms, response_status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (client_ip, user_agent, endpoint, ip_count, response_time_ms, status_code),
        )
    except Exception as e:
        logger.warning(f"Failed to log pull request: {e}")
