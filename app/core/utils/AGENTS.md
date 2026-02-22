# UTILS KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

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
