"""
Monitoring module for Blacklist application

Updated: 2025-11-21 (Error Handling Standardization - HIGH PRIORITY #4)
"""

from .metrics import (
    setup_metrics,
    metrics_view,
    track_blacklist_query,
    track_db_operation,
    update_entries_count,
)

# Error metrics (Phase 4: Error Monitoring)
from .error_metrics import error_metrics, ErrorMetricsCollector

__all__ = [
    "setup_metrics",
    "metrics_view",
    "track_blacklist_query",
    "track_db_operation",
    "update_entries_count",
    "error_metrics",
    "ErrorMetricsCollector",
]
