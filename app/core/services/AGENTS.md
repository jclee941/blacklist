# SERVICES KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

14 services, manual DI via `ServiceFactory` (`service_factory.py`, 278L). All registered on `current_app.extensions['service_name']`.

## INIT ORDER (STRICT)

1. **Infra**: `database_service`, `redis_service`
2. **Dependents**: `blacklist_service`, `analytics_service`
3. **Collection**: `collection_service`, `collection_history`, `collection_status`
4. **Integration**: `fortimanager_push_service`, `fortigate_service`
5. **Config**: `credential_service`, `secure_credential_service`
6. **Business**: `scoring_service`, `export_service`
7. **Admin**: `admin_service`, `monitoring_service`

## KEY FILES

| File                           | LOC | Role                                   |
| ------------------------------ | --- | -------------------------------------- |
| `blacklist_service.py`         | 534 | core CRUD + scoring (complexity 39.43) |
| `collection_service.py`        | 596 | collection orchestration               |
| `database_service.py`          | 460 | raw SQL query execution                |
| `secure_credential_service.py` | 624 | AES-256-GCM credential storage         |
| `service_factory.py`           | 278 | DI container, init ordering            |

## CONVENTIONS

- Access: `current_app.extensions['service_name']` — never import directly.
- Init order violations cause runtime errors (dependency not yet registered).
- Services receive dependencies via constructor injection from `ServiceFactory`.

## ANTI-PATTERNS

- `from app.core.services import X` in route code (circular import risk).
- Direct instantiation in request handlers (bypass DI container).
- Changing init order without verifying dependency graph.

## NOTES

- DI violations: `fortimanager_push_service.py` + `settings_service.py` (intentional, optional `db_service` param).
- `admin_routes.py` DI violation fixed in v3.6.3.
