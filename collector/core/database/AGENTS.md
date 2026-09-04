# COLLECTOR DATABASE KNOWLEDGE BASE

## OVERVIEW

Persistence and credential boundary for the collector. `service.py` owns the pooled connection and REGTECH credential decryption; `queries.py` (`DatabaseQueryMixin`) supplies the filtering/dedup/batch-insert helpers mixed into `DatabaseService`.

## FILES

| File | Role |
| --- | --- |
| `service.py` | `DatabaseService`: pooled `psycopg2` connections, credential read/decrypt, `save_blacklist_ips`, `record_collection_history`, stats queries |
| `queries.py` | `DatabaseQueryMixin`: private/invalid-IP filtering, dedup, batched `ON CONFLICT` upserts |

## CREDENTIAL BOUNDARY

- REGTECH credentials come from `collector_regtech_credentials` only, via `DatabaseService.get_collection_credentials` (health/API paths) and `CollectorConfig.get_regtech_credentials` (config-cache path). Neither has an environment-variable or file fallback; both fail closed — an empty result or `ValueError` — when the row is missing.
- Encrypted passwords use Fernet with a PBKDF2-SHA256 key derived from `CREDENTIAL_MASTER_KEY` + `ENCRYPTION_SALT`; decryption runs only when the row's `encrypted` flag is set.
- `CollectorConfig.clear_credentials_cache()` scrubs the in-memory cache; use it on shutdown instead of letting the process exit with plaintext resident.

## RUNTIME DB ROLE

`postgres/configure-runtime-roles.sh` grants the collector's Postgres role explicit per-table ACLs only — no blanket privileges, and `CREATE` on `public` is revoked:

| Table | Grant |
| --- | --- |
| `blacklist_ips` | SELECT, INSERT, UPDATE, DELETE |
| `collector_regtech_credentials` | SELECT only — the collector never writes credentials |
| `collection_history`, `collection_stats`, `collection_status` | SELECT, INSERT, UPDATE |
| `regtech_monitoring`, `regtech_alerts` | SELECT, INSERT |

Schema changes belong in `postgres/migrations/`; the collector role cannot `CREATE`/`ALTER` at runtime.

## CONVENTIONS

- Parameterized queries only; batch inserts chunk via `CollectorConfig.BATCH_SIZE`.
- `ON CONFLICT (...) DO UPDATE` for every upsert (`_fallback_batch_insert`).
- IP filtering excludes private/loopback/link-local/reserved ranges and already-expired `removal_date` rows before insert.

## ANTI-PATTERNS

- Adding a credential fallback (env var, file, hardcoded default) outside `collector_regtech_credentials`.
- Writing to `collector_regtech_credentials` from collector code — the grant is read-only by design.
- Running DDL/`ALTER TABLE` from collector code at runtime; schema changes go in `postgres/` migrations.
- Importing `app/core/services/database_service.py` — separate role, separate pool, collector isolation.
