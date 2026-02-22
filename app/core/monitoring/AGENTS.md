# MONITORING KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

Prometheus metrics infrastructure. 1124 lines across 3 modules + `__init__.py`.

## FILES

| File               | LOC | Role                                                  |
| ------------------ | --- | ----------------------------------------------------- |
| `metrics.py`       | 412 | Counter, Histogram, Gauge for API/DB/collection ops   |
| `cache_metrics.py` | 397 | Redis hit/miss tracking, cache invalidation metrics   |
| `error_metrics.py` | 289 | `ErrorMetricsCollector` — error rate by type/endpoint |

## CONVENTIONS

- Lazy init via `_metrics_cache` pattern to prevent duplicate Prometheus collector registration.
- `/metrics` endpoint is `@public` (no JWT required).
- Korean comments.

## ANTI-PATTERNS

- Registering Prometheus collectors without checking `_metrics_cache` (causes `ValueError: Duplicated timeseries`).
- Creating metric instances outside lazy-init pattern.
