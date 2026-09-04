from datetime import datetime
from typing import Any, Dict


STRUCTURE_KEYS = [
    "forms",
    "tables",
    "inputs",
    "selects",
    "buttons",
    "scripts",
    "css_links",
]


def create_monitoring_error(message: str) -> Dict[str, Any]:
    return {
        "success": False,
        "error": message,
        "timestamp": datetime.now().isoformat(),
    }


def create_availability_error(message: str) -> Dict[str, Any]:
    return {
        "timestamp": datetime.now().isoformat(),
        "status": "error",
        "error_messages": [message],
    }
