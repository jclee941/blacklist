# AGENTS.md — Core Utilities

**Generated:** 2026-02-11
**Commit:** 2b9662f | **Version:** 3.5.59
**Parent:** `app/core/` | **Total:** 1,198 lines

## OVERVIEW

Cross-cutting utilities used by services and routes. Standardized response formatting, caching, encryption, validation, and logging.

## STRUCTURE

| File | Lines | Purpose |
|------|-------|---------|
| `response_utils.py` | 287 | Standardized API response wrappers |
| `encryption.py` | 238 | AES-256-GCM credential encryption |
| `cache_utils.py` | 204 | Redis caching with Prometheus metrics |
| `logger_config.py` | 150 | Structured logging setup |
| `db_utils.py` | 131 | `execute_query()`, `execute_write()` helpers |
| `validators.py` | 70 | IP/input validation |
| `version.py` | 45 | VERSION file reader |
| `error_handlers.py` | 26 | Flask error handler registration |
| `__init__.py` | 47 | Re-exports all public APIs |

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Return API response | `response_utils.py` | `success_response()`, `paginated_response()`, etc. |
| Add Redis caching | `cache_utils.py` | `@cached` decorator, `get_redis_client()` |
| Encrypt/decrypt credentials | `encryption.py` | AES-256-GCM, key from env |
| Raw SQL execution | `db_utils.py` | Wraps `db_service` with error handling |
| Validate IP addresses | `validators.py` | Validation helpers |
| Configure logging | `logger_config.py` | Called during app init |

## CONVENTIONS

- **Response format**: All API responses use `success_response()` → `{success: true, data: {...}, timestamp: "...", request_id: "..."}`
- **Caching**: `@cached` decorator wraps functions with Redis + Prometheus metrics integration
- **Redis**: Lazy connection via `get_redis_client()`, env vars `REDIS_HOST`/`REDIS_PORT`
- **Korean comments**: `cache_utils.py` and `logger_config.py` have Korean docstrings
- **Exports**: `__init__.py` re-exports everything — import from `utils` not individual files

## ANTI-PATTERNS

| Forbidden | Alternative |
|-----------|-------------|
| `jsonify()` in routes directly | `success_response(data)` from `response_utils` |
| Manual Redis connection | `get_redis_client()` from `cache_utils` |
| `print()` for logging | `logger_config` structured logging |
| Direct `psycopg2` calls | `execute_query()`/`execute_write()` from `db_utils` |

## NOTES

- `error_handlers.py` is minimal (26L) — just registers Flask error handlers, actual error classes in `errors/` and `exceptions/`
- `encryption.py` uses Fernet (AES-256-GCM) — encryption key from `ENCRYPTION_KEY` env var
- `version.py` reads from root `VERSION` file (currently `3.5.59`)
