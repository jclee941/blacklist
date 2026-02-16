"""
Collection API Utilities
Shared helper functions for Collection routes
"""

import logging
import requests
from typing import Dict, Any, Optional

from ....config import config

logger = logging.getLogger(__name__)

COLLECTOR_SERVICE_URL = config.COLLECTOR_URL


def interval_seconds_to_string(seconds: int) -> str:
    """Convert interval seconds to UI-friendly string"""
    if seconds == 3600:
        return "hourly"
    elif seconds == 86400:
        return "daily"
    elif seconds == 604800:
        return "weekly"
    else:
        return "daily"  # default


def interval_string_to_seconds(interval_str: str) -> int:
    """Convert UI interval string to seconds"""
    if interval_str == "hourly":
        return 3600
    elif interval_str == "daily":
        return 86400
    elif interval_str == "weekly":
        return 604800
    else:
        return 86400  # default to daily


def call_collector_api(endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Call collector service API"""
    try:
        url = f"{COLLECTOR_SERVICE_URL}{endpoint}"

        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            return {"success": False, "error": f"Unsupported method: {method}"}

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "success": False,
                "error": f"Collector API error: {response.status_code}",
                "details": response.text,
            }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Cannot connect to collector service",
            "details": "Collector container may be down or unhealthy",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
