# UTILS KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** cd16ec1
**Branch:** master | **Version:** 3.6.8

## OVERVIEW

Cross-cutting utilities. 1198 lines across 8 modules + `__init__.py`.

## FILES

| File                | LOC | Role                                                                |
| ------------------- | --- | ------------------------------------------------------------------- |
| `response_utils.py` | 287 | standardized API responses `{success, data, timestamp, request_id}` |
| `encryption.py`     | 238 | AES-256-GCM + Fernet for credential storage                         |
| `cache_utils.py`    | 204 | Redis decorator + Prometheus cache metrics integration              |
| `logger_config.py`  | 150 | structured JSON logging configuration                               |
| `db_utils.py`       | 131 | `execute_query` / `execute_write` helpers for raw SQL               |
| `validators.py`     | 70  | IP address validation                                               |
| `version.py`        | 45  | `VERSION` file reader                                               |
| `error_handlers.py` | 26  | Flask error handler registration                                    |

## RESPONSE FORMAT

```json
{"success": true, "data": {...}, "timestamp": "ISO8601", "request_id": "uuid"}
```

## CONVENTIONS

- Korean docstrings mixed with English.
- All DB queries through `db_utils.py` helpers (parameterized `%s`).
- Cache decorator auto-integrates with Prometheus metrics.

## ANTI-PATTERNS

- Direct `cursor.execute()` calls — use `db_utils.execute_query/execute_write`.
- Manual response dict construction — use `response_utils` helpers.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `success_response` | function | `response_utils.py:14` | high | standardized `{success, data, timestamp, request_id}` |
| `execute_query` | function | `db_utils.py:63` | high | parameterized SELECT helper |
| `execute_write` | function | `db_utils.py:88` | high | parameterized INSERT/UPDATE/DELETE helper |
| `CacheManager` | class | `cache_utils.py:77` | med | Redis cache with Prometheus integration |
| `cached` | decorator | `cache_utils.py:177` | med | TTL-based cache decorator |
| `validate_ip` | function | `validators.py:9` | med | IP address validation |