# POSTGRES KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

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
