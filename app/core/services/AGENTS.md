# SERVICES KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** cd16ec1
**Branch:** master | **Version:** 5.0.0

## OVERVIEW

14 services, manual DI via `ServiceFactory` (`service_factory.py`, 278L). All registered on `current_app.extensions['service_name']`.

## INIT ORDER (STRICT)

1. **Infra**: `database_service`, `redis_service`
2. **Dependents**: `blacklist_service`, `analytics_service`
3. **Collection**: `collection_service`, `collection_history`, `collection_status`
4. **Integration**: `fortigate_service`
5. **Config**: `credential_service`, `secure_credential_service`
6. **Business**: `scoring_service`, `export_service`
7. **Admin**: `admin_service`, `monitoring_service`

## KEY FILES

| File                           | Role                                                          |
| ------------------------------ | ------------------------------------------------------------- |
| `blacklist_service.py`         | core service: cache, queries, whitelist, stats (mixin host)   |
| `blacklist_service_collection.py` | collection/sync mixin (extracted)                            |
| `blacklist_service_health.py`  | health/stats mixin (extracted)                                |
| `blacklist_service_sync.py`    | collector sync + bulk upsert                                  |
| `collection_service.py`        | collection orchestration                                      |
| `database_service.py`          | raw SQL query execution                                       |
| `secure_credential_service.py` | AES-256-GCM credential storage                                |
| `settings_service.py`          | system_settings CRUD + cache (DB-over-env precedence for admin credentials) |
| `service_factory.py`           | DI container, init ordering                                   |

## CONVENTIONS

- Access: `current_app.extensions['service_name']` — never import directly.
- Init order violations cause runtime errors (dependency not yet registered).
- Services receive dependencies via constructor injection from `ServiceFactory`.

## ANTI-PATTERNS

- `from app.core.services import X` in route code (circular import risk).
- Direct instantiation in request handlers (bypass DI container).
- Changing init order without verifying dependency graph.

## NOTES



## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `BlacklistService` | class | `blacklist_service.py:37` | high | core CRUD + sync + system stats (complexity 39.43) |
| `CollectionService` | class | `collection_service.py:31` | high | collection orchestration across sources |
| `SecureCredentialService` | class | `secure_credential_service.py:30` | high | AES-256-GCM credential storage (624L) |
| `SettingsService` | class | `settings_service.py:21` | med | system settings CRUD |
| `ThreatScoringService` | class | `scoring_service.py:14` | med | IP threat scoring engine |
| `initialize_services` | function | `service_factory.py:37` | high | DI container, strict init order |
