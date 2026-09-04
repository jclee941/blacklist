# DATABASE KNOWLEDGE BASE

## OVERVIEW

PostgreSQL connection management layer. psycopg2 direct — no ORM.

## CONNECTION MANAGERS

| Class                         | Features                                         |
| ----------------------------- | ------------------------------------------------ |
| `SmartConnectionManager`      | backoff 60s, cached stats 300s, max 5 error logs |
| `PostgreSQLConnectionManager` | basic env-var driven, simpler fallback           |

## CODE MAP

| Symbol                        | Type     | Location                     | Refs | Role                                     |
| ----------------------------- | -------- | ---------------------------- | ---- | ---------------------------------------- |
| `SmartConnectionManager`      | class    | `connection_pool_manager.py` | high | pooled connections + exponential backoff |
| `PostgreSQLConnectionManager` | class    | `connection_recovery.py`     | med  | basic recovery + reconnection fallback   |
| `get_db_connection`           | function | `connection.py`              | high | connection factory entry point           |
| `_get_connection_params`      | function | `connection.py`              | med  | env priority resolution                  |

## ENV PRIORITY

`DATABASE_URL` → `POSTGRES_URL` → individual vars (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`).

## FILES

- `connection_pool_manager.py` — SmartConnectionManager
- `connection_recovery.py` — recovery + reconnection logic
- `schema/complete-schema.sql`: reference schema

## CONVENTIONS

- Korean docstrings.
- Raw SQL only, parameterized `%s`.
- Connection pooling via psycopg2 `ThreadedConnectionPool`.

## NOTES

- Separate from `postgres/` (schema/migrations) and `collector/core/database/` (collector's own pooled connections and DB role, see that package's `AGENTS.md`).
