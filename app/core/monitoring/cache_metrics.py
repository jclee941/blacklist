"""
Cache Metrics Collector
Tracks cache hit/miss rates, latency, and provides monitoring capabilities

Created: 2025-11-21 (Redis Query Caching - MEDIUM PRIORITY #8)
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict, deque
from threading import Lock
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CacheEvent:
    """Represents a single cache operation event"""

    timestamp: str
    operation: str  # 'hit', 'miss', 'set', 'delete', 'error'
    cache_key: str
    endpoint: Optional[str] = None
    latency_ms: Optional[float] = None
    ttl: Optional[int] = None


class CacheMetricsCollector:
    """
    Collects and tracks cache metrics for monitoring and performance analysis.

    Thread-safe singleton for tracking cache operations across the application.
    Maintains a rolling window of recent operations and aggregated statistics.
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

        # Rolling window of recent cache operations (max 10000 events)
        self._recent_operations: deque = deque(maxlen=10000)

        # Cache hit/miss counters
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._cache_sets: int = 0
        self._cache_deletes: int = 0
        self._cache_errors: int = 0

        # Latency tracking (milliseconds)
        self._hit_latencies: deque = deque(maxlen=1000)
        self._miss_latencies: deque = deque(maxlen=1000)

        # Cache operations by endpoint
        self._endpoint_hits: Dict[str, int] = defaultdict(int)
        self._endpoint_misses: Dict[str, int] = defaultdict(int)

        # Cache operations by key prefix
        self._prefix_hits: Dict[str, int] = defaultdict(int)
        self._prefix_misses: Dict[str, int] = defaultdict(int)

        # Total cache sizes (approximate)
        self._cache_size_bytes: int = 0

        # First operation timestamp
        self._start_time: datetime = datetime.now()

        # Thread safety lock for metrics updates
        self._metrics_lock = Lock()

        logger.info("Cache metrics collector initialized")

    def record_hit(self, cache_key: str, latency_ms: float, endpoint: Optional[str] = None) -> None:
        """
        Record a cache hit event.

        Args:
            cache_key: The cache key that was hit
            latency_ms: Latency in milliseconds for cache retrieval
            endpoint: Optional API endpoint path
        """
        with self._metrics_lock:
            # Create cache event
            event = CacheEvent(
                timestamp=datetime.now().isoformat(),
                operation="hit",
                cache_key=cache_key,
                endpoint=endpoint,
                latency_ms=latency_ms,
            )

            # Add to recent operations
            self._recent_operations.append(event)

            # Update counters
            self._cache_hits += 1
            self._hit_latencies.append(latency_ms)

            if endpoint:
                self._endpoint_hits[endpoint] += 1

            # Extract key prefix (before first ':')
            prefix = cache_key.split(":")[0] if ":" in cache_key else cache_key
            self._prefix_hits[prefix] += 1

    def record_miss(self, cache_key: str, latency_ms: float, endpoint: Optional[str] = None) -> None:
        """
        Record a cache miss event.

        Args:
            cache_key: The cache key that was missed
            latency_ms: Latency in milliseconds for cache lookup
            endpoint: Optional API endpoint path
        """
        with self._metrics_lock:
            # Create cache event
            event = CacheEvent(
                timestamp=datetime.now().isoformat(),
                operation="miss",
                cache_key=cache_key,
                endpoint=endpoint,
                latency_ms=latency_ms,
            )

            # Add to recent operations
            self._recent_operations.append(event)

            # Update counters
            self._cache_misses += 1
            self._miss_latencies.append(latency_ms)

            if endpoint:
                self._endpoint_misses[endpoint] += 1

            # Extract key prefix
            prefix = cache_key.split(":")[0] if ":" in cache_key else cache_key
            self._prefix_misses[prefix] += 1

    def record_set(self, cache_key: str, ttl: int, size_bytes: Optional[int] = None) -> None:
        """
        Record a cache set operation.

        Args:
            cache_key: The cache key being set
            ttl: Time-to-live in seconds
            size_bytes: Optional size of cached value in bytes
        """
        with self._metrics_lock:
            event = CacheEvent(timestamp=datetime.now().isoformat(), operation="set", cache_key=cache_key, ttl=ttl)

            self._recent_operations.append(event)
            self._cache_sets += 1

            if size_bytes:
                self._cache_size_bytes += size_bytes

    def record_delete(self, cache_key: str) -> None:
        """Record a cache delete operation"""
        with self._metrics_lock:
            event = CacheEvent(timestamp=datetime.now().isoformat(), operation="delete", cache_key=cache_key)

            self._recent_operations.append(event)
            self._cache_deletes += 1

    def record_error(self, cache_key: str, operation: str, error_message: str) -> None:
        """
        Record a cache error.

        Args:
            cache_key: The cache key involved
            operation: The operation that failed ('get', 'set', 'delete')
            error_message: Error message
        """
        with self._metrics_lock:
            self._cache_errors += 1
            logger.warning(f"Cache {operation} error for key '{cache_key}': {error_message}")

    def get_statistics(self) -> Dict:
        """
        Get aggregated cache statistics.

        Returns:
            Dict containing cache statistics:
            - total_operations: Total cache operations
            - cache_hits: Total cache hits
            - cache_misses: Total cache misses
            - hit_rate: Cache hit rate (%)
            - avg_hit_latency_ms: Average hit latency
            - avg_miss_latency_ms: Average miss latency
            - by_endpoint: Hit/miss stats by endpoint
            - by_prefix: Hit/miss stats by cache key prefix
            - uptime_hours: Hours since metrics collection started
        """
        with self._metrics_lock:
            total_ops = self._cache_hits + self._cache_misses
            hit_rate = (self._cache_hits / total_ops * 100) if total_ops > 0 else 0

            avg_hit_latency = sum(self._hit_latencies) / len(self._hit_latencies) if self._hit_latencies else 0

            avg_miss_latency = sum(self._miss_latencies) / len(self._miss_latencies) if self._miss_latencies else 0

            uptime = datetime.now() - self._start_time
            uptime_hours = uptime.total_seconds() / 3600

            # Build endpoint statistics
            endpoint_stats = {}
            all_endpoints = set(list(self._endpoint_hits.keys()) + list(self._endpoint_misses.keys()))

            for endpoint in all_endpoints:
                hits = self._endpoint_hits.get(endpoint, 0)
                misses = self._endpoint_misses.get(endpoint, 0)
                total = hits + misses

                endpoint_stats[endpoint] = {
                    "hits": hits,
                    "misses": misses,
                    "hit_rate": round((hits / total * 100) if total > 0 else 0, 2),
                }

            # Build prefix statistics
            prefix_stats = {}
            all_prefixes = set(list(self._prefix_hits.keys()) + list(self._prefix_misses.keys()))

            for prefix in all_prefixes:
                hits = self._prefix_hits.get(prefix, 0)
                misses = self._prefix_misses.get(prefix, 0)
                total = hits + misses

                prefix_stats[prefix] = {
                    "hits": hits,
                    "misses": misses,
                    "hit_rate": round((hits / total * 100) if total > 0 else 0, 2),
                }

            return {
                "total_operations": total_ops,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_sets": self._cache_sets,
                "cache_deletes": self._cache_deletes,
                "cache_errors": self._cache_errors,
                "hit_rate": round(hit_rate, 2),
                "avg_hit_latency_ms": round(avg_hit_latency, 2),
                "avg_miss_latency_ms": round(avg_miss_latency, 2),
                "by_endpoint": endpoint_stats,
                "by_prefix": prefix_stats,
                "uptime_hours": round(uptime_hours, 2),
                "collection_start": self._start_time.isoformat(),
            }

    def get_recent_operations(
        self, limit: int = 50, operation_type: Optional[str] = None, endpoint: Optional[str] = None
    ) -> List[Dict]:
        """
        Get recent cache operations with optional filtering.

        Args:
            limit: Maximum number of operations to return
            operation_type: Filter by operation type ('hit', 'miss', 'set', 'delete')
            endpoint: Filter by endpoint

        Returns:
            List of cache event dictionaries
        """
        with self._metrics_lock:
            operations = list(self._recent_operations)

        # Apply filters
        if operation_type:
            operations = [o for o in operations if o.operation == operation_type]

        if endpoint:
            operations = [o for o in operations if o.endpoint == endpoint]

        # Apply limit and convert to dict
        return [asdict(o) for o in operations[-limit:]]

    def get_cache_trends(self, window_minutes: int = 60, bucket_minutes: int = 5) -> Dict:
        """
        Get cache performance trends over time.

        Args:
            window_minutes: Time window to analyze (default: 60 minutes)
            bucket_minutes: Size of time buckets (default: 5 minutes)

        Returns:
            Dict containing:
            - buckets: List of time buckets with hit/miss counts
            - total_in_window: Total operations in the time window
        """
        with self._metrics_lock:
            operations = list(self._recent_operations)

        # Calculate time boundaries
        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)

        # Filter operations within window
        recent = [o for o in operations if datetime.fromisoformat(o.timestamp) >= window_start]

        # Create buckets
        buckets = []
        bucket_size = timedelta(minutes=bucket_minutes)
        current_bucket_start = window_start

        while current_bucket_start < now:
            bucket_end = current_bucket_start + bucket_size

            # Count operations in this bucket
            bucket_ops = [o for o in recent if current_bucket_start <= datetime.fromisoformat(o.timestamp) < bucket_end]

            hits = sum(1 for o in bucket_ops if o.operation == "hit")
            misses = sum(1 for o in bucket_ops if o.operation == "miss")
            total = hits + misses

            buckets.append(
                {
                    "start": current_bucket_start.isoformat(),
                    "end": bucket_end.isoformat(),
                    "hits": hits,
                    "misses": misses,
                    "hit_rate": round((hits / total * 100) if total > 0 else 0, 2),
                }
            )

            current_bucket_start = bucket_end

        return {
            "buckets": buckets,
            "total_in_window": len(recent),
            "window_minutes": window_minutes,
            "bucket_minutes": bucket_minutes,
        }

    def get_top_keys(self, by: str = "hits", limit: int = 10) -> List[Dict]:
        """
        Get top cache keys by various criteria.

        Args:
            by: Sorting criteria ('hits' or 'misses')
            limit: Number of top items to return

        Returns:
            List of top cache keys with counts
        """
        with self._metrics_lock:
            if by == "hits":
                data = self._prefix_hits
            elif by == "misses":
                data = self._prefix_misses
            else:
                raise ValueError(f"Invalid 'by' parameter: {by}")

            # Sort by count descending
            sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:limit]

            return [{"prefix": prefix, "count": count} for prefix, count in sorted_items]

    def reset_metrics(self) -> None:
        """Reset all metrics (use with caution)"""
        with self._metrics_lock:
            self._recent_operations.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            self._cache_sets = 0
            self._cache_deletes = 0
            self._cache_errors = 0
            self._hit_latencies.clear()
            self._miss_latencies.clear()
            self._endpoint_hits.clear()
            self._endpoint_misses.clear()
            self._prefix_hits.clear()
            self._prefix_misses.clear()
            self._cache_size_bytes = 0
            self._start_time = datetime.now()

        logger.warning("Cache metrics have been reset")


# Global singleton instance
cache_metrics = CacheMetricsCollector()
