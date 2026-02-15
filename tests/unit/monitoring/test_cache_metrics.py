"""Unit tests for core.monitoring.cache_metrics."""

import time
from datetime import datetime
from unittest.mock import patch

import pytest

from core.monitoring.cache_metrics import CacheMetricsCollector, CacheEvent


class TestCacheEvent:
    """Tests for CacheEvent dataclass."""

    def test_create_cache_event(self):
        event = CacheEvent(
            timestamp=datetime.now(),
            operation="hit",
            cache_key="blacklist:8.8.8.8",
        )
        assert event.operation == "hit"
        assert event.cache_key == "blacklist:8.8.8.8"

    def test_optional_fields_default_none(self):
        event = CacheEvent(
            timestamp=datetime.now(),
            operation="miss",
            cache_key="test:key",
        )
        assert event.endpoint is None
        assert event.latency_ms is None
        assert event.ttl is None

    def test_with_all_fields(self):
        event = CacheEvent(
            timestamp=datetime.now(),
            operation="set",
            cache_key="test:key",
            endpoint="/api/check",
            latency_ms=1.5,
            ttl=300,
        )
        assert event.endpoint == "/api/check"
        assert event.latency_ms == 1.5
        assert event.ttl == 300


class TestCacheMetricsCollector:
    """Tests for CacheMetricsCollector."""

    def _make_collector(self):
        """Create a fresh collector (bypass singleton)."""
        import collections as _collections
        import threading

        collector = CacheMetricsCollector.__new__(CacheMetricsCollector)
        collector._metrics_lock = threading.Lock()
        collector._recent_operations = _collections.deque(maxlen=10000)
        collector._cache_hits = 0
        collector._cache_misses = 0
        collector._cache_sets = 0
        collector._cache_deletes = 0
        collector._cache_errors = 0
        collector._hit_latencies = _collections.deque(maxlen=1000)
        collector._miss_latencies = _collections.deque(maxlen=1000)
        collector._endpoint_hits = _collections.defaultdict(int)
        collector._endpoint_misses = _collections.defaultdict(int)
        collector._prefix_hits = _collections.defaultdict(int)
        collector._prefix_misses = _collections.defaultdict(int)
        collector._cache_size_bytes = 0
        collector._start_time = datetime.now()
        collector._initialized = True
        return collector

    def test_record_hit(self):
        collector = self._make_collector()
        collector.record_hit("blacklist:1.2.3.4", latency_ms=0.5)
        assert collector._cache_hits == 1

    def test_record_miss(self):
        collector = self._make_collector()
        collector.record_miss("blacklist:5.6.7.8", latency_ms=1.0)
        assert collector._cache_misses == 1

    def test_record_set(self):
        collector = self._make_collector()
        collector.record_set("blacklist:1.2.3.4", ttl=300)
        assert collector._cache_sets == 1

    def test_record_delete(self):
        collector = self._make_collector()
        collector.record_delete("blacklist:1.2.3.4")
        assert collector._cache_deletes == 1

    def test_record_error(self):
        collector = self._make_collector()
        collector.record_error("blacklist:1.2.3.4", "get", "connection timeout")
        assert collector._cache_errors == 1

    def test_get_statistics(self):
        collector = self._make_collector()
        collector.record_hit("key1", 0.5)
        collector.record_miss("key2", 1.0)
        collector.record_set("key1", 300)
        stats = collector.get_statistics()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["cache_sets"] == 1
        assert "hit_rate" in stats
        assert "uptime_hours" in stats

    def test_hit_rate_calculation(self):
        collector = self._make_collector()
        collector.record_hit("key1", 0.5)
        collector.record_hit("key2", 0.3)
        collector.record_miss("key3", 1.0)
        stats = collector.get_statistics()
        # 2 hits / 3 total = 66.67%
        assert 60 < stats["hit_rate"] < 70

    def test_get_statistics_empty(self):
        collector = self._make_collector()
        stats = collector.get_statistics()
        assert stats["total_operations"] == 0
        assert stats["cache_hits"] == 0

    def test_get_recent_operations(self):
        collector = self._make_collector()
        collector.record_hit("key1", 0.5)
        collector.record_set("key1", 300)
        recent = collector.get_recent_operations(limit=10)
        assert len(recent) == 2

    def test_get_recent_operations_with_filter(self):
        collector = self._make_collector()
        collector.record_hit("key1", 0.5)
        collector.record_miss("key2", 1.0)
        collector.record_set("key1", 300)
        recent = collector.get_recent_operations(operation_type="hit")
        assert len(recent) == 1

    def test_get_top_keys(self):
        collector = self._make_collector()
        collector.record_hit("prefix1:key1", 0.5)
        collector.record_hit("prefix1:key2", 0.3)
        collector.record_hit("prefix2:key1", 0.4)
        top = collector.get_top_keys(by="hits", limit=10)
        assert isinstance(top, list)
        assert len(top) >= 1

    def test_reset_metrics(self):
        collector = self._make_collector()
        collector.record_hit("key1", 0.5)
        collector.record_miss("key2", 1.0)
        collector.reset_metrics()
        assert collector._cache_hits == 0
        assert collector._cache_misses == 0
        assert len(collector._recent_operations) == 0

    def test_get_cache_trends(self):
        collector = self._make_collector()
        collector.record_hit("key1", 0.5)
        trends = collector.get_cache_trends(window_minutes=60, bucket_minutes=5)
        assert isinstance(trends, dict)
        assert "buckets" in trends

    def test_record_hit_with_endpoint(self):
        collector = self._make_collector()
        collector.record_hit("key1", 0.5, endpoint="/api/check")
        assert collector._endpoint_hits.get("/api/check", 0) >= 1
