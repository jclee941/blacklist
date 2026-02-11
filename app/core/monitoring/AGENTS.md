# AGENTS.md — Monitoring & Metrics

**Generated:** 2026-02-11
**Commit:** 3f44350 | **Version:** 3.5.57
**Parent:** `app/core/` | **Total:** 1,124 lines

## OVERVIEW

Prometheus metrics collection for Flask app. Three metric domains: request/business metrics, cache performance, error tracking.

## STRUCTURE

| File | Lines | Purpose |
|------|-------|---------|
| `metrics.py` | 412 | Core Prometheus metrics (Counter/Histogram/Gauge), request tracking |
| `cache_metrics.py` | 397 | Redis cache hit/miss rates, latency tracking |
| `error_metrics.py` | 289 | Error rate tracking, `ErrorMetricsCollector` class |
| `__init__.py` | 26 | Re-exports: `setup_metrics`, `track_*`, `ErrorMetricsCollector` |

## WHERE TO LOOK

| Task | File |
|------|------|
| Add new Prometheus metric | `metrics.py` — use `_metrics_cache` pattern |
| Track cache performance | `cache_metrics.py` — integrated with `cache_utils.py` |
| Track error rates | `error_metrics.py` — `ErrorMetricsCollector` |
| Wire metrics into app | `metrics.py` → `setup_metrics()` called during app init |
| Expose `/metrics` endpoint | `metrics.py` → `metrics_view()` |

## CONVENTIONS

- **Lazy initialization**: All metrics use `_metrics_cache` dict to prevent duplicate registration (Flask app factory pattern causes re-imports)
- **`_metric_exists(name)`**: Checks Prometheus registry for existing metric by name (handles `_total`, `_created`, `_bucket` suffixes)
- **Import pattern**: Always import from `__init__.py`, never from individual files
- **Korean comments**: Present throughout (`포트폴리오용 실제 비즈니스 메트릭 수집`)

## ANTI-PATTERNS

| Forbidden | Why |
|-----------|-----|
| Creating metrics at module level | Causes duplicate registration errors — use `_metrics_cache` |
| Direct `REGISTRY` manipulation | Use helper functions in `metrics.py` |
| Skipping `_metric_exists()` check | Will crash on second Flask app creation |

## NOTES

- Metrics endpoint is `@public` (no JWT required) — exposed at `/metrics`
- `cache_metrics.py` is tightly coupled with `utils/cache_utils.py` — they share the same Redis connection
- Error Handling Standardization Phase 4 refactored exports in `__init__.py`
