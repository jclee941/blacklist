# DATABASE KNOWLEDGE BASE

**Generated:** 2026-02-25 15:26 Asia/Seoul
**Commit:** e50fb74
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

PostgreSQL connection management layer. psycopg2 direct — no ORM.

## CONNECTION MANAGERS

| Class                         | LOC | Features                                         |
| ----------------------------- | --- | ------------------------------------------------ |
| `SmartConnectionManager`      | 228 | backoff 60s, cached stats 300s, max 5 error logs |
| `PostgreSQLConnectionManager` | 152 | basic env-var driven, simpler fallback           |

## CODE MAP

| Symbol                        | Type     | Location                        | Refs | Role                                     |
| ----------------------------- | -------- | ------------------------------- | ---- | ---------------------------------------- |
| `SmartConnectionManager`      | class    | `connection_pool_manager.py:17` | high | pooled connections + exponential backoff |
| `PostgreSQLConnectionManager` | class    | `connection_recovery.py:15`     | med  | basic recovery + reconnection fallback   |
| `get_db_connection`           | function | `connection.py:18`              | high | connection factory entry point           |
| `_get_connection_params`      | function | `connection.py:14`              | med  | env priority resolution                  |

## ENV PRIORITY

`DATABASE_URL` → `POSTGRES_URL` → individual vars (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`).

## FILES

- `connection_pool_manager.py` — SmartConnectionManager
- `connection_recovery.py` — recovery + reconnection logic
- `schema/complete-schema.sql` — ~400L reference schema

## CONVENTIONS

- Korean docstrings.
- Raw SQL only, parameterized `%s`.
- Connection pooling via psycopg2 `ThreadedConnectionPool`.

## KNOWN ISSUES

- Hardcoded `"localhost"` in fallback hosts list (`connection_pool_manager.py:75`, `connection_recovery.py:27`) — identified for future config extraction.
- Print statements in recovery code — should use `logger.info()`.

## NOTES

- Separate from `postgres/` (schema/migrations) and `collector/core/database.py` (collector connections).
