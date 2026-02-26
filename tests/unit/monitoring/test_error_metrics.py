"""Unit tests for core.monitoring.error_metrics."""

from datetime import datetime


from core.monitoring.error_metrics import ErrorMetricsCollector, ErrorEvent


class TestErrorEvent:
    """Tests for ErrorEvent dataclass."""

    def test_create_error_event(self):
        event = ErrorEvent(
            timestamp=datetime.now(),
            exception_type="ValueError",
            status_code=400,
            endpoint="/api/test",
            method="GET",
            message="bad request",
        )
        assert event.exception_type == "ValueError"
        assert event.status_code == 400
        assert event.endpoint == "/api/test"

    def test_optional_fields_default_none(self):
        event = ErrorEvent(
            timestamp=datetime.now(),
            exception_type="RuntimeError",
            status_code=500,
            endpoint="/api/crash",
            method="POST",
            message="internal error",
        )
        assert event.request_id is None
        assert event.user_agent is None

    def test_with_optional_fields(self):
        event = ErrorEvent(
            timestamp=datetime.now(),
            exception_type="AuthError",
            status_code=401,
            endpoint="/api/auth",
            method="GET",
            message="unauthorized",
            request_id="req-123",
            user_agent="Mozilla/5.0",
        )
        assert event.request_id == "req-123"
        assert event.user_agent == "Mozilla/5.0"


class TestErrorMetricsCollector:
    """Tests for ErrorMetricsCollector."""

    def _make_collector(self):
        """Create a fresh collector (bypass singleton)."""
        import collections as _collections
        import threading

        collector = ErrorMetricsCollector.__new__(ErrorMetricsCollector)
        collector._metrics_lock = threading.Lock()
        collector._recent_errors = _collections.deque(maxlen=1000)
        collector._error_counts = _collections.defaultdict(int)
        collector._endpoint_errors = _collections.defaultdict(int)
        collector._status_code_counts = _collections.defaultdict(int)
        collector._total_errors = 0
        collector._start_time = datetime.now()
        return collector

    def test_record_error(self):
        collector = self._make_collector()
        collector.record_error(
            exception_type="ValueError",
            status_code=400,
            endpoint="/api/test",
            method="GET",
            message="bad input",
        )
        assert collector._total_errors == 1
        assert len(collector._recent_errors) == 1

    def test_record_multiple_errors(self):
        collector = self._make_collector()
        for i in range(5):
            collector.record_error(
                exception_type="RuntimeError",
                status_code=500,
                endpoint=f"/api/endpoint{i}",
                method="GET",
                message=f"error {i}",
            )
        assert collector._total_errors == 5
        assert len(collector._recent_errors) == 5

    def test_get_statistics(self):
        collector = self._make_collector()
        collector.record_error(
            exception_type="ValueError",
            status_code=400,
            endpoint="/api/test",
            method="GET",
            message="bad input",
        )
        stats = collector.get_statistics()
        assert stats["total_errors"] == 1
        assert "by_type" in stats
        assert "by_endpoint" in stats
        assert "by_status_code" in stats
        assert "uptime_hours" in stats

    def test_get_statistics_empty(self):
        collector = self._make_collector()
        stats = collector.get_statistics()
        assert stats["total_errors"] == 0

    def test_get_recent_errors(self):
        collector = self._make_collector()
        collector.record_error(
            exception_type="ValueError",
            status_code=400,
            endpoint="/api/test",
            method="GET",
            message="bad input",
        )
        recent = collector.get_recent_errors(limit=10)
        assert len(recent) == 1
        assert recent[0]["exception_type"] == "ValueError"

    def test_get_recent_errors_with_filter(self):
        collector = self._make_collector()
        collector.record_error(
            exception_type="ValueError",
            status_code=400,
            endpoint="/api/a",
            method="GET",
            message="val error",
        )
        collector.record_error(
            exception_type="RuntimeError",
            status_code=500,
            endpoint="/api/b",
            method="POST",
            message="runtime error",
        )
        recent = collector.get_recent_errors(exception_type="ValueError")
        assert len(recent) == 1
        assert recent[0]["exception_type"] == "ValueError"

    def test_get_top_errors_by_type(self):
        collector = self._make_collector()
        for _ in range(3):
            collector.record_error("ValueError", 400, "/a", "GET", "v")
        for _ in range(1):
            collector.record_error("RuntimeError", 500, "/b", "GET", "r")
        top = collector.get_top_errors(by="type", limit=10)
        assert isinstance(top, list)
        assert len(top) >= 1
        # Returns List[Dict] with 'key' and 'count' keys
        assert top[0]["key"] == "ValueError"
        assert top[0]["count"] == 3

    def test_reset_metrics(self):
        collector = self._make_collector()
        collector.record_error("ValueError", 400, "/a", "GET", "v")
        collector.reset_metrics()
        assert collector._total_errors == 0
        assert len(collector._recent_errors) == 0

    def test_get_error_trends(self):
        collector = self._make_collector()
        collector.record_error("ValueError", 400, "/a", "GET", "v")
        trends = collector.get_error_trends(window_minutes=60, bucket_minutes=5)
        assert isinstance(trends, dict)
        assert "buckets" in trends
