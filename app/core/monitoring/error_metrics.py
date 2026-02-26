"""
Error Metrics Collector
Tracks error rates, exception types, and provides monitoring capabilities

Created: 2025-11-21 (Error Handling Standardization - HIGH PRIORITY #4)
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict, deque
from threading import Lock
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ErrorEvent:
    """Represents a single error event"""

    timestamp: str
    exception_type: str
    status_code: int
    endpoint: str
    method: str
    message: str
    request_id: Optional[str] = None
    user_agent: Optional[str] = None


class ErrorMetricsCollector:
    """
    Collects and tracks error metrics for monitoring and alerting.

    Thread-safe singleton for tracking error events across the application.
    Maintains a rolling window of recent errors and aggregated statistics.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # Rolling window of recent errors (max 1000 events)
        self._recent_errors: deque = deque(maxlen=1000)

        # Error counts by type
        self._error_counts: Dict[str, int] = defaultdict(int)

        # Error counts by endpoint
        self._endpoint_errors: Dict[str, int] = defaultdict(int)

        # Error counts by status code
        self._status_code_counts: Dict[int, int] = defaultdict(int)

        # Total error count
        self._total_errors: int = 0

        # First error timestamp
        self._start_time: datetime = datetime.now()

        # Thread safety lock for metrics updates
        self._metrics_lock = Lock()

        logger.info("Error metrics collector initialized")

    def record_error(
        self,
        exception_type: str,
        status_code: int,
        endpoint: str,
        method: str,
        message: str,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Record an error event.

        Args:
            exception_type: Type of exception (e.g., 'DatabaseError')
            status_code: HTTP status code
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            message: Error message
            request_id: Optional request ID for tracing
            user_agent: Optional user agent string
        """
        with self._metrics_lock:
            # Create error event
            event = ErrorEvent(
                timestamp=datetime.now().isoformat(),
                exception_type=exception_type,
                status_code=status_code,
                endpoint=endpoint,
                method=method,
                message=message,
                request_id=request_id,
                user_agent=user_agent,
            )

            # Add to recent errors
            self._recent_errors.append(event)

            # Update counters
            self._error_counts[exception_type] += 1
            self._endpoint_errors[endpoint] += 1
            self._status_code_counts[status_code] += 1
            self._total_errors += 1

    def get_statistics(self) -> Dict:
        """
        Get aggregated error statistics.

        Returns:
            Dict containing error statistics:
            - total_errors: Total number of errors recorded
            - error_rate: Errors per hour
            - by_type: Error counts grouped by exception type
            - by_endpoint: Error counts grouped by endpoint
            - by_status_code: Error counts grouped by status code
            - uptime_hours: Hours since metrics collection started
        """
        with self._metrics_lock:
            uptime = datetime.now() - self._start_time
            uptime_hours = uptime.total_seconds() / 3600

            return {
                "total_errors": self._total_errors,
                "error_rate": round(self._total_errors / uptime_hours, 2) if uptime_hours > 0 else 0,
                "by_type": dict(self._error_counts),
                "by_endpoint": dict(self._endpoint_errors),
                "by_status_code": dict(self._status_code_counts),
                "uptime_hours": round(uptime_hours, 2),
                "collection_start": self._start_time.isoformat(),
            }

    def get_recent_errors(
        self,
        limit: int = 50,
        exception_type: Optional[str] = None,
        endpoint: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        Get recent error events with optional filtering.

        Args:
            limit: Maximum number of errors to return
            exception_type: Filter by exception type
            endpoint: Filter by endpoint
            since: Filter by timestamp (errors after this time)

        Returns:
            List of error event dictionaries
        """
        with self._metrics_lock:
            errors = list(self._recent_errors)

        # Apply filters
        if exception_type:
            errors = [e for e in errors if e.exception_type == exception_type]

        if endpoint:
            errors = [e for e in errors if e.endpoint == endpoint]

        if since:
            since_iso = since.isoformat()
            errors = [e for e in errors if e.timestamp >= since_iso]

        # Apply limit and convert to dict
        return [asdict(e) for e in errors[-limit:]]

    def get_error_trends(self, window_minutes: int = 60, bucket_minutes: int = 5) -> Dict:
        """
        Get error trends over time.

        Args:
            window_minutes: Time window to analyze (default: 60 minutes)
            bucket_minutes: Size of time buckets (default: 5 minutes)

        Returns:
            Dict containing:
            - buckets: List of time buckets with error counts
            - total_in_window: Total errors in the time window
        """
        with self._metrics_lock:
            errors = list(self._recent_errors)

        # Calculate time boundaries
        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)

        # Filter errors within window
        recent = [e for e in errors if datetime.fromisoformat(e.timestamp) >= window_start]

        # Create buckets
        buckets = []
        bucket_size = timedelta(minutes=bucket_minutes)
        current_bucket_start = window_start

        while current_bucket_start < now:
            bucket_end = current_bucket_start + bucket_size

            # Count errors in this bucket
            bucket_errors = [
                e for e in recent if current_bucket_start <= datetime.fromisoformat(e.timestamp) < bucket_end
            ]

            buckets.append(
                {
                    "start": current_bucket_start.isoformat(),
                    "end": bucket_end.isoformat(),
                    "count": len(bucket_errors),
                    "by_type": self._count_by_type(bucket_errors),
                }
            )

            current_bucket_start = bucket_end

        return {
            "buckets": buckets,
            "total_in_window": len(recent),
            "window_minutes": window_minutes,
            "bucket_minutes": bucket_minutes,
        }

    def _count_by_type(self, errors: List[ErrorEvent]) -> Dict[str, int]:
        """Count errors by exception type"""
        counts = defaultdict(int)
        for error in errors:
            counts[error.exception_type] += 1
        return dict(counts)

    def get_top_errors(self, by: str = "type", limit: int = 10) -> List[Dict]:
        """
        Get top errors by various criteria.

        Args:
            by: Grouping criteria ('type', 'endpoint', or 'status_code')
            limit: Number of top items to return

        Returns:
            List of top error items with counts
        """
        with self._metrics_lock:
            if by == "type":
                data = self._error_counts
            elif by == "endpoint":
                data = self._endpoint_errors
            elif by == "status_code":
                data = self._status_code_counts
            else:
                raise ValueError(f"Invalid 'by' parameter: {by}")

            # Sort by count descending
            sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:limit]

            return [{"key": key, "count": count} for key, count in sorted_items]

    def reset_metrics(self) -> None:
        """Reset all metrics (use with caution)"""
        with self._metrics_lock:
            self._recent_errors.clear()
            self._error_counts.clear()
            self._endpoint_errors.clear()
            self._status_code_counts.clear()
            self._total_errors = 0
            self._start_time = datetime.now()

        logger.warning("Error metrics have been reset")


# Global singleton instance
error_metrics = ErrorMetricsCollector()
