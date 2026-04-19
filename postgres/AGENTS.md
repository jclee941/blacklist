# POSTGRES KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** cd16ec1
**Branch:** master | **Version:** 3.6.9

## OVERVIEW

Raw SQL migrations + schema initialization. No ORM — project policy.

## STRUCTURE

```text
postgres/
├── initdb/
│   ├── 01-extensions.sql    # pg_trgm, uuid-ossp
│   ├── 02-schema.sql        # 17 tables, 50+ indexes
│   └── 03-migrations.sql    # bootstrap migrations
└── migrations/
    ├── 001_*.sql
    ├── 002_*.sql
    └── ... through 006_*.sql
```

## INIT SEQUENCE

`01-extensions.sql` → `02-schema.sql` → `03-migrations.sql` (run once on fresh DB).

## MIGRATION STRATEGY

- Sequential numbered: `NNN_description.sql` (001–006).
- Additive only — no `DROP` statements in migrations.
- `IF NOT EXISTS` for idempotent table/index creation.
- `ON CONFLICT DO UPDATE` for seed data.

## CORE TABLES

`blacklist_ips`, `collection_history`, `collection_credentials`, `collection_status`, `credentials` (AES-256-GCM), `whitelist_ips`, `unified_ip_list`, `fortigate_devices`, `fortigate_pull_logs`, `system_settings`, plus monitoring/metrics tables.

## EXTENSIONS

- `pg_trgm` — trigram text search.
- `uuid-ossp` — UUID generation.

## CONVENTIONS

- Raw SQL only, parameterized `%s`.
- All queries use `IF NOT EXISTS` guards.
- `ON CONFLICT DO UPDATE` for upserts.

## NOTES

- Separate from `app/core/database/` (connection management) and `collector/core/database.py` (collector connections).
- 17 tables with 50+ indexes defined in `02-schema.sql`.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `02-schema.sql` | DDL | `initdb/02-schema.sql` | high | 17 tables + 50 indexes (source of truth) |
| `01-extensions.sql` | DDL | `initdb/01-extensions.sql` | med | pg_trgm + uuid-ossp bootstrap |
| `03-migrations.sql` | DDL | `initdb/03-migrations.sql` | med | initial migration state |