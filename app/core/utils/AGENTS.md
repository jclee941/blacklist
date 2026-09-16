# UTILS KNOWLEDGE BASE

## OVERVIEW

Cross-cutting utilities for responses, caching, encryption, logging, rate limits, validation, and version lookup.

## FILES

| File                | Role                                                 |
| ------------------- | ---------------------------------------------------- |
| `response_utils.py` | Standard API response helpers + `safe_error_message` |
| `encryption.py`     | Credential encryption helpers                        |
| `cache_utils.py`    | Cache manager and `cached` decorator                 |
| `logger_config.py`  | Application logging configuration                    |
| `rate_limit.py`     | Rate-limit decorators and configuration              |
| `validators.py`     | IP, pagination, and string validation helpers        |
| `version.py`        | `VERSION` file lookup                                |

## RESPONSE FORMAT

```json
{"success": true, "data": {...}, "timestamp": "ISO8601", "request_id": "uuid"}
```

## CONVENTIONS

- Korean docstrings mixed with English.
- Cache decorator auto-integrates with Prometheus metrics.

## ANTI-PATTERNS

- Manual response dict construction — use `response_utils` helpers.
- Returning `str(exception)` in a response body — psycopg2 text carries SQL, table, and column names. Use `safe_error_message(exc)` and log the detail.

## CODE MAP

| Symbol               | Type      | Location            | Refs | Role                                                              |
| -------------------- | --------- | ------------------- | ---- | ----------------------------------------------------------------- |
| `success_response`   | function  | `response_utils.py` | high | Standard response envelope                                        |
| `safe_error_message` | function  | `response_utils.py` | med  | Client-safe exception text; raw exception detail stays in the log |
| `CacheManager`       | class     | `cache_utils.py`    | med  | Redis-backed cache manager                                        |
| `cached`             | decorator | `cache_utils.py`    | med  | TTL-based caching                                                 |
| `validate_ip`        | function  | `validators.py`     | med  | IP address validation                                             |
