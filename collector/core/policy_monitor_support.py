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

MONITORING_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS regtech_monitoring (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        structure_data JSONB,
        availability_data JSONB,
        change_analysis JSONB,
        alert_sent BOOLEAN DEFAULT FALSE
    )
"""

ALERTS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS regtech_alerts (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        alert_type VARCHAR(50),
        message TEXT,
        details JSONB,
        resolved BOOLEAN DEFAULT FALSE
    )
"""


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
