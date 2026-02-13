# SERVICE LAYER KNOWLEDGE BASE

**Generated:** 2026-02-12
**Commit:** 83e7d28 | **Version:** 3.5.60
**Parent:** [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW

Business logic core. **Manual DI** — `ServiceFactory` injects 14 service dependencies. Circular imports strictly forbidden.

## LIFECYCLE (Strict Order)

```
1. Infra       → database_service, redis_service
2. Dependents  → blacklist_service, analytics_service
3. Collection  → collection_service, scheduler_service
4. Integration → fortimanager_service, fortigate_service
5. Config      → credential_service, secure_credential_service
6. Business    → scoring_service, export_service
7. Admin       → admin_service, monitoring_service
```

⚠️ Order change FORBIDDEN — based on dependency graph.

## HOW TO: Add New Service

```python
# 1. app/core/services/my_service.py
class MyService:
    def __init__(self, db_service):
        self.db = db_service

# 2. Register in service_factory.py
def _init_my_service(self):
    from core.services.my_service import MyService
    self.my_service = MyService(self.db_service)
    self.app.extensions['my_service'] = self.my_service

# 3. Use in routes
service = current_app.extensions['my_service']
```

## ANTI-PATTERNS

| Forbidden | Alternative |
|-----------|-------------|
| Direct cross-service calls | ServiceFactory injection |

## KNOWN ISSUES

| Issue | Severity |
|-------|----------|
| `blacklist_service.py` complexity 39.43 | HIGH |
| DI violations: `admin_routes.py`, `fortimanager_push_service.py`, `settings_service.py` | INTENTIONAL |
| `blacklist_service.py` 3 hardcoded URLs (L420, L462, L510) | CRITICAL |

## KEY FILES

| File | Lines | Role |
|------|-------|------|
| `blacklist_service.py` | 562L | IP business logic ⚠️ |
| `database_service.py` | 460L | ThreadedConnectionPool |
| `service_factory.py` | 278L | DI container |
