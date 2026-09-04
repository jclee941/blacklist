# POSTGRES KNOWLEDGE BASE

## OVERVIEW

Raw SQL migrations plus schema init, no ORM. `configure-runtime-roles.sh` is installed as a first-init hook and is also invoked explicitly by the installer on each deployment.

## STRUCTURE

- `initdb/01-extensions.sql` - `pg_trgm`, `uuid-ossp`.
- `initdb/02-schema.sql` - 14 tables, 49 indexes; base schema source of truth.
- `initdb/03-migrations.sql` - bootstrap migration state applied on fresh DBs.
- `migrations/001..008_*.sql` - sequential, additive-only files using `IF NOT EXISTS` / `ON CONFLICT DO UPDATE`.
- `configure-runtime-roles.sh` - applies migrations 007 and 008, then bootstraps roles; idempotent, runs on first `initdb` and from `install.sh`, not on ordinary restarts.
- `configure-tls.sh` - writes `pg_hba.conf` forcing `hostssl scram-sha-256` and rejecting `hostnossl`.
- `tls-entrypoint.sh`, `Dockerfile` - TLS-enabled Postgres 15 image.

## ROLE MODEL (`configure-runtime-roles.sh`)

Runs once on first `initdb`, and again on each `install.sh` deployment after `blacklist-postgres` reports healthy:

- `blacklist_owner` - `NOLOGIN`, owns every table, view, and sequence; never connects directly.
- `blacklist_app` - `LOGIN`, `SELECT`/`INSERT`/`UPDATE`/`DELETE` on all tables plus full sequence usage.
- `blacklist_collector` - `LOGIN`, scoped grants only: full DML on `blacklist_ips`; `SELECT` on `collector_regtech_credentials`; `SELECT`/`INSERT`/`UPDATE` on `collection_history`, `collection_stats`, `collection_status`; `SELECT`/`INSERT` on `regtech_monitoring`, `regtech_alerts`.
- `PUBLIC` and both app roles are denied `CREATE` on schema `public`; default privileges revoke collector access to any future app-owned object.
- The script rejects duplicate role names and is safe to re-run.

## Migrations 007/008

- `007_align_ip_schema_contracts.sql` - adds `is_active NOT NULL DEFAULT TRUE` to `whitelist_ips` and `blacklist_ips`; adds a unique index on `whitelist_ips.ip_address` and on `blacklist_ips(ip_address, source)`.
- `008_add_regtech_monitoring.sql` - adds `regtech_monitoring`/`regtech_alerts`; creates `collector_regtech_credentials` as a `security_barrier` view over `collection_credentials` filtered to `service_name = 'REGTECH'`. This view is the only path `blacklist_collector` has to REGTECH credentials.

## Conventions

- Additive only; migrations never contain `DROP`.
- `IF NOT EXISTS` / `ON CONFLICT DO UPDATE` for idempotency.
- No runtime DDL from app or collector code; schema changes go through numbered migration files applied by `configure-runtime-roles.sh`.
- Raw SQL with parameterized `%s` queries in application code.

## Notes

- Separate from `app/core/database/` (app connection pooling) and `collector/core/database/` (collector connections); this directory owns only DDL and roles, not runtime query code.
