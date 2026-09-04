# SERVICES KNOWLEDGE BASE

## OVERVIEW

14 services, manual DI via `initialize_services()` (`service_factory.py`). All registered on `current_app.extensions['service_name']`.

## INIT ORDER (STRICT)

1. **Core infra**: `db_service`
2. **Depends on db_service**: `blacklist_service`, `analytics_service`
3. **Collection**: `collection_service`, `scheduler_service`
4. **Integration**: `cloudflare_service`
5. **Configuration**: `secure_credential_service`, `regtech_config_service`, `settings_service`, `auth_state_service`
6. **Business logic**: `scoring_service`, `expiry_service`, `ab_test_service`, `optimized_blacklist_service`

Hard-fail (no try/except around construction, so an error aborts app startup): `db_service`, `blacklist_service`, `collection_service`, `secure_credential_service`, `regtech_config_service`, `settings_service`, `auth_state_service`.
Soft-fail (constructed inside try/except, so an error is logged and the service is omitted from the container): `analytics_service`, `scheduler_service`, `cloudflare_service`, `scoring_service`, `expiry_service`, `ab_test_service`, `optimized_blacklist_service`.

## KEY FILES

| File                               | Role                                                          |
| ----------------------------------- | -------------------------------------------------------------- |
| `service_factory.py`               | `initialize_services()` DI container, strict init order       |
| `blacklist_service.py`             | core service: cache, queries, whitelist, stats (mixin host)   |
| `blacklist_service_collection.py`  | collection/sync mixin (extracted)                              |
| `blacklist_service_health.py`      | health/stats mixin (extracted)                                 |
| `blacklist_service_sync.py`        | collector sync + bulk upsert                                   |
| `auth_state_service.py`            | transactional admin credential + session-version state (fails closed) |
| `collection_service.py`            | collection orchestration                                       |
| `database_service.py`              | raw SQL query execution                                        |
| `secure_credential_service.py`     | Fernet-based credential storage                                 |
| `settings_service.py`              | non-auth `system_settings` CRUD + cache                         |

## CODE MAP

| Symbol                    | Type     | Location                    | Refs | Role                                             |
| -------------------------- | -------- | ----------------------------- | ---- | -------------------------------------------------- |
| `initialize_services`     | function | `service_factory.py`      | high | DI container, strict init order                  |
| `BlacklistService`        | class    | `blacklist_service.py`    | high | core CRUD + sync + system stats                  |
| `AuthStateService`        | class    | `auth_state_service.py`   | high | transactional password/session read+rotate, fails closed via `AuthStateUnavailableError` |
| `CollectionService`       | class    | `collection_service.py`   | high | collection orchestration across sources          |
| `SecureCredentialService` | class    | `secure_credential_service.py` | high | Fernet-based credential storage                  |
| `SettingsService`         | class    | `settings_service.py`     | med  | system settings CRUD                              |
| `ThreatScoringService`    | class    | `scoring_service.py`      | med  | IP threat scoring engine                          |

## CONVENTIONS

- Access: `current_app.extensions['service_name']` — never import directly.
- Init order violations cause runtime errors (dependency not yet registered).
- Services receive dependencies via constructor injection from `service_factory.initialize_services()`.
- `AuthStateService` writes go through `pg_advisory_xact_lock` + a single DB transaction; DB errors raise `AuthStateUnavailableError` and never fall back to env credentials.

## ANTI-PATTERNS

- `from app.core.services import X` in route code (circular import risk).
- Direct instantiation in request handlers (bypass DI container).
- Changing init order without verifying the dependency graph in `service_factory.py`.
