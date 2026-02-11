# AGENTS.md — Database Connection Layer

**Generated:** 2026-02-11
**Commit:** 2b9662f | **Version:** 3.5.59
**Parent:** `app/core/` | **Total:** 403 lines + schema

## OVERVIEW

PostgreSQL connection management for the Flask app. Two connection manager classes with env-var-based config, backoff, and error suppression. Separate from `postgres/` (migrations) and `collector/core/database.py` (collector's own pool).

## STRUCTURE

| File | Lines | Purpose |
|------|-------|---------|
| `connection_pool_manager.py` | 228 | `SmartConnectionManager` — production pool with backoff/caching |
| `connection_recovery.py` | 152 | `PostgreSQLConnectionManager` — basic env-var connection |
| `connection.py` | 22 | Legacy connection helper |
| `schema/complete-schema.sql` | ~400 | Full database schema reference |

## WHERE TO LOOK

| Task | File |
|------|------|
| Connection pool issues | `connection_pool_manager.py` — `SmartConnectionManager` |
| Connection string parsing | Both managers parse `DATABASE_URL` / `POSTGRES_URL` env vars |
| Schema reference | `schema/complete-schema.sql` |
| Add new table | `postgres/migrations/` (NOT here) |

## CONVENTIONS

- **Two connection managers** exist (intentional):
  - `SmartConnectionManager`: Production — backoff (60s), cached stats (300s), max 5 error logs, error suppression
  - `PostgreSQLConnectionManager`: Simpler — env-var parsing, no backoff
- **Env var priority**: `DATABASE_URL` → `POSTGRES_URL` → individual `POSTGRES_HOST`/`POSTGRES_PORT`/`POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD`
- **psycopg2**: Direct driver usage — no ORM, no SQLAlchemy
- **Korean docstrings**: Both manager classes documented in Korean

## ANTI-PATTERNS

| Forbidden | Alternative |
|-----------|-------------|
| Hardcoded connection strings | Always env vars |
| Schema changes here | Use `postgres/migrations/` for DDL |

## NOTES

- `SmartConnectionManager._max_error_logs = 5` — silences repeated connection failures after 5 log entries
- `SmartConnectionManager._backoff_duration = 60` — skips connection attempts for 60s after failure
- This layer is used by `database_service.py` (in services/) which is the DI-registered service
- Collector has its own independent `database.py` (maxconn=20) — no shared connections
