# MONITORING KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** cd16ec1
**Branch:** master | **Version:** 3.6.9

## OVERVIEW

Prometheus metrics infrastructure. 1124 lines across 3 modules + `__init__.py`.

## FILES

| File               | LOC | Role                                                  |
| ------------------ | --- | ----------------------------------------------------- |
| `metrics.py`       | 412 | Counter, Histogram, Gauge for API/DB/collection ops   |
| `cache_metrics.py` | 397 | Redis hit/miss tracking, cache invalidation metrics   |
| `error_metrics.py` | 289 | `ErrorMetricsCollector` — error rate by type/endpoint |

## CODE MAP

| Symbol                  | Type      | Location              | Refs | Role                                          |
| ----------------------- | --------- | --------------------- | ---- | --------------------------------------------- |
| `CacheMetricsCollector` | class     | `cache_metrics.py:31` | med  | singleton Redis hit/miss/invalidation tracker |
| `ErrorMetricsCollector` | class     | `error_metrics.py:33` | med  | singleton error rate by type/endpoint         |
| `CacheEvent`            | dataclass | `cache_metrics.py:20` | med  | cache operation event data carrier            |
| `ErrorEvent`            | dataclass | `error_metrics.py:20` | med  | error occurrence event data carrier           |

## CONVENTIONS

- Lazy init via `_metrics_cache` pattern to prevent duplicate Prometheus collector registration.
- `/metrics` endpoint is `@public` (no JWT required).
- Korean comments.

## ANTI-PATTERNS

- Registering Prometheus collectors without checking `_metrics_cache` (causes `ValueError: Duplicated timeseries`).
- Creating metric instances outside lazy-init pattern.
