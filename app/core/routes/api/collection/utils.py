import logging
import time
import requests
from typing import Dict, Any, Optional

from ....config import config

logger = logging.getLogger(__name__)

COLLECTOR_SERVICE_URL = config.COLLECTOR_URL
MAX_RETRIES = 3
BACKOFF_BASE_DELAY = 1.0


def interval_seconds_to_string(seconds: int) -> str:
    if seconds == 3600:
        return "hourly"
    elif seconds == 86400:
        return "daily"
    elif seconds == 604800:
        return "weekly"
    else:
        return "daily"


def interval_string_to_seconds(interval_str: str) -> int:
    if interval_str == "hourly":
        return 3600
    elif interval_str == "daily":
        return 86400
    elif interval_str == "weekly":
        return 604800
    else:
        return 86400


def call_collector_api(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    *,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    url = f"{COLLECTOR_SERVICE_URL}{endpoint}"
    if method not in ("GET", "POST"):
        return {"success": False, "error": f"Unsupported method: {method}"}

    max_attempts = MAX_RETRIES if method == "GET" else 1

    for attempt in range(1, max_attempts + 1):
        try:
            if method == "GET":
                response = requests.get(url, timeout=timeout or 10, **config.COLLECTOR_AUTH_REQUEST_KWARGS)
            else:
                response = requests.post(
                    url,
                    json=data,
                    timeout=timeout or 30,
                    **config.COLLECTOR_AUTH_REQUEST_KWARGS,
                )
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"Collector API error: {response.status_code}",
                }

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < max_attempts:
                delay = BACKOFF_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Collector %s %s attempt %d/%d failed: %s — retrying in %.1fs",
                    method,
                    endpoint,
                    attempt,
                    max_attempts,
                    e,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error("Collector %s %s failed after %d attempts: %s", method, endpoint, max_attempts, e)
        except Exception as e:
            logger.error("Collector API call failed for %s %s: %s", method, endpoint, e)
            return {"success": False, "error": "Collector request failed"}

    return {
        "success": False,
        "error": "Cannot connect to collector service",
    }
