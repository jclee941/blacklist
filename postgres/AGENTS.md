# POSTGRES KNOWLEDGE BASE

**Generated:** 2026-02-08
**Role:** Database Schema & Migrations
**Parent:** [../AGENTS.md](../AGENTS.md)

## OVERVIEW

PostgreSQL 15 with Raw SQL only. **ORM forbidden** — SQLAlchemy/Prisma not allowed.
Migrations are sequential numbered SQL files.

## STRUCTURE

```
postgres/
├── Dockerfile              # PostgreSQL 15 + extensions
├── initdb/                 # Initial schema (fresh DB)
│   ├── 01-extensions.sql   # pg_trgm, uuid-ossp
│   ├── 02-schema.sql       # Core tables
│   └── 03-migrations.sql   # Migration tracking
└── migrations/             # Incremental changes
    ├── 001_add_data_source_column.sql
    ├── 002_add_missing_columns.sql
    └── 003_add_display_order.sql
```

## HOW TO: Add Migration

```bash
# 1. Create: migrations/004_description.sql (NNN sequential, snake_case)
# 2. Apply:
docker compose exec blacklist-db psql -U blacklist -d blacklist -f /migrations/004_description.sql
```

Include comment header with purpose and date. Use `IF NOT EXISTS` for idempotency.

## CONVENTIONS

| Convention | Description |
|------------|-------------|
| SQL only | No ORM, no query builders |
| Parameterized | Always `%s` placeholders (never string concat) |
| Sequential | Never skip migration numbers |
| Idempotent | `IF NOT EXISTS` where possible |
| No DROP | Add columns only, never destructive |

## CORE TABLES

| Table | Purpose |
|-------|---------|
| `blacklist` | IP/domain blacklist entries |
| `collection_history` | ETL collection logs |
| `users` | Admin users |
| `credentials` | Encrypted API keys (AES-256-GCM) |
| `sources` | Data source configurations |

## INITDB SEQUENCE

`01-extensions.sql` → `02-schema.sql` → `03-migrations.sql` → `migrations/*.sql` (in order)

## NOTES

- Connection pool: managed by `app/core/services/database_service.py`
- Schema changes require PR review
- Backups handled by infrastructure, not application
