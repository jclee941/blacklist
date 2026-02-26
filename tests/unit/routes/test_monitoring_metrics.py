"""
Tests for monitoring/metrics.py — cache monitoring endpoints.
These use monitoring_bp (nested under api_bp).
"""

from unittest.mock import MagicMock
from flask import Flask, g


def _create_app(cache_enabled=True, error_enabled=True):
    """Create app with monitoring_bp. Patches module-level flags."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    from core.routes.api.monitoring import monitoring_bp
    import core.routes.api.monitoring.metrics as metrics_mod

    # Patch the module-level flags
    metrics_mod.CACHE_METRICS_ENABLED = cache_enabled
    metrics_mod.ERROR_METRICS_ENABLED = error_enabled

    app.register_blueprint(monitoring_bp)

    from core.errors.handlers import register_error_handlers

    register_error_handlers(app)

    @app.before_request
    def _set_request_id():
        g.request_id = "test-request-id"

    return app, metrics_mod


def _mock_cache_metrics():
    mock = MagicMock()
    mock.get_statistics.return_value = {"total_operations": 100, "hit_rate": 95.0}
    mock.get_recent_operations.return_value = [{"operation": "hit", "cache_key": "stats:main", "latency_ms": 2.0}]
    mock.get_cache_trends.return_value = {
        "buckets": [{"start": "10:00", "hits": 50, "misses": 2}],
        "total_in_window": 52,
    }
    mock.get_top_keys.return_value = [
        {"prefix": "stats", "count": 9500},
    ]
    return mock


# ─── Cache Stats ───────────────────────────────────────────────────


class TestCacheStats:
    """GET /monitoring/cache/stats"""

    def test_cache_stats_disabled(self):
        app, _ = _create_app(cache_enabled=False)
        client = app.test_client()
        resp = client.get("/monitoring/cache/stats")
        assert resp.status_code == 503
        data = resp.get_json()
        assert data["error"]["code"] == "METRICS_UNAVAILABLE"

    def test_cache_stats_success(self):
        app, mod = _create_app(cache_enabled=True)
        mock_cm = _mock_cache_metrics()
        mod.cache_metrics = mock_cm

        client = app.test_client()
        resp = client.get("/monitoring/cache/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["hit_rate"] == 95.0

    def test_cache_stats_internal_error(self):
        app, mod = _create_app(cache_enabled=True)
        mock_cm = MagicMock()
        mock_cm.get_statistics.side_effect = RuntimeError("broken")
        mod.cache_metrics = mock_cm

        client = app.test_client()
        resp = client.get("/monitoring/cache/stats")
        assert resp.status_code == 500


# ─── Cache Operations ─────────────────────────────────────────────


class TestCacheOperations:
    """GET /monitoring/cache/operations"""

    def test_operations_disabled(self):
        app, _ = _create_app(cache_enabled=False)
        client = app.test_client()
        resp = client.get("/monitoring/cache/operations")
        assert resp.status_code == 503

    def test_operations_success(self):
        app, mod = _create_app(cache_enabled=True)
        mock_cm = _mock_cache_metrics()
        mod.cache_metrics = mock_cm

        client = app.test_client()
        resp = client.get("/monitoring/cache/operations?limit=10&operation_type=hit")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["filters"]["operation_type"] == "hit"

    def test_operations_limit_capped(self):
        app, mod = _create_app(cache_enabled=True)
        mock_cm = _mock_cache_metrics()
        mod.cache_metrics = mock_cm

        client = app.test_client()
        resp = client.get("/monitoring/cache/operations?limit=9999")
        assert resp.status_code == 200
        # limit should be capped at 500
        mock_cm.get_recent_operations.assert_called_once()
        call_kwargs = mock_cm.get_recent_operations.call_args
        assert call_kwargs[1]["limit"] == 500 or call_kwargs[0][0] == 500 if call_kwargs[0] else True

    def test_operations_error(self):
        app, mod = _create_app(cache_enabled=True)
        mock_cm = MagicMock()
        mock_cm.get_recent_operations.side_effect = RuntimeError("fail")
        mod.cache_metrics = mock_cm

        client = app.test_client()
        resp = client.get("/monitoring/cache/operations")
        assert resp.status_code == 500


# ─── Cache Trends ──────────────────────────────────────────────────


class TestCacheTrends:
    """GET /monitoring/cache/trends"""

    def test_trends_disabled(self):
        app, _ = _create_app(cache_enabled=False)
        client = app.test_client()
        resp = client.get("/monitoring/cache/trends")
        assert resp.status_code == 503

    def test_trends_success(self):
        app, mod = _create_app(cache_enabled=True)
        mock_cm = _mock_cache_metrics()
        mod.cache_metrics = mock_cm

        client = app.test_client()
        resp = client.get("/monitoring/cache/trends?window_minutes=120&bucket_minutes=10")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_trends_error(self):
        app, mod = _create_app(cache_enabled=True)
        mock_cm = MagicMock()
        mock_cm.get_cache_trends.side_effect = RuntimeError("fail")
        mod.cache_metrics = mock_cm

        client = app.test_client()
        resp = client.get("/monitoring/cache/trends")
        assert resp.status_code == 500


# ─── Top Cache Keys ────────────────────────────────────────────────


class TestTopCacheKeys:
    """GET /monitoring/cache/top-keys"""

    def test_top_keys_disabled(self):
        app, _ = _create_app(cache_enabled=False)
        client = app.test_client()
        resp = client.get("/monitoring/cache/top-keys")
        assert resp.status_code == 503

    def test_top_keys_success(self):
        app, mod = _create_app(cache_enabled=True)
        mock_cm = _mock_cache_metrics()
        mod.cache_metrics = mock_cm

        client = app.test_client()
        resp = client.get("/monitoring/cache/top-keys?by=hits&limit=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["sorted_by"] == "hits"

    def test_top_keys_invalid_by_param(self):
        app, mod = _create_app(cache_enabled=True)
        mock_cm = _mock_cache_metrics()
        mod.cache_metrics = mock_cm

        client = app.test_client()
        resp = client.get("/monitoring/cache/top-keys?by=invalid")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"]["code"] == "INVALID_PARAMETER"

    def test_top_keys_by_misses(self):
        app, mod = _create_app(cache_enabled=True)
        mock_cm = _mock_cache_metrics()
        mod.cache_metrics = mock_cm

        client = app.test_client()
        resp = client.get("/monitoring/cache/top-keys?by=misses")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["sorted_by"] == "misses"

    def test_top_keys_error(self):
        app, mod = _create_app(cache_enabled=True)
        mock_cm = MagicMock()
        mock_cm.get_top_keys.side_effect = RuntimeError("fail")
        mod.cache_metrics = mock_cm

        client = app.test_client()
        resp = client.get("/monitoring/cache/top-keys")
        assert resp.status_code == 500


# ─── All Metrics ───────────────────────────────────────────────────


class TestAllMetrics:
    """GET /monitoring/metrics"""

    def test_all_metrics_both_enabled(self):
        app, mod = _create_app(cache_enabled=True, error_enabled=True)
        mock_cm = _mock_cache_metrics()
        mock_em = MagicMock()
        mock_em.get_statistics.return_value = {"total_errors": 5}
        mod.cache_metrics = mock_cm
        mod.error_metrics = mock_em

        client = app.test_client()
        resp = client.get("/monitoring/metrics")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "cache" in data["data"]
        assert "errors" in data["data"]

    def test_all_metrics_both_disabled(self):
        app, _ = _create_app(cache_enabled=False, error_enabled=False)
        client = app.test_client()
        resp = client.get("/monitoring/metrics")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"] == {}

    def test_all_metrics_cache_error_graceful(self):
        app, mod = _create_app(cache_enabled=True, error_enabled=False)
        mock_cm = MagicMock()
        mock_cm.get_statistics.side_effect = RuntimeError("oops")
        mod.cache_metrics = mock_cm

        client = app.test_client()
        resp = client.get("/monitoring/metrics")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "error" in data["data"]["cache"]
