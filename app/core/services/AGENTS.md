# SERVICE LAYER KNOWLEDGE BASE

**Generated:** 2026-02-08
**Commit:** 450d20c | **Version:** 3.5.39
**Parent:** [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW

비즈니스 로직 중심. **Manual DI** — `ServiceFactory`가 14 서비스 의존성 주입. 순환 Import 엄금.

## LIFECYCLE (엄격한 순서)

```
1. Infra       → database_service, redis_service
2. Dependents  → blacklist_service, analytics_service
3. Collection  → collection_service, scheduler_service
4. Integration → fortimanager_service, fortigate_service
5. Config      → credential_service, secure_credential_service
6. Business    → scoring_service, export_service
7. Admin       → admin_service, monitoring_service
```

⚠️ 순서 변경 금지 — 의존성 그래프 기반.

## HOW TO: 새 서비스 추가

```python
# 1. app/core/services/my_service.py
class MyService:
    def __init__(self, db_service):
        self.db = db_service

# 2. service_factory.py에 등록
def _init_my_service(self):
    from core.services.my_service import MyService
    self.my_service = MyService(self.db_service)
    self.app.extensions['my_service'] = self.my_service

# 3. 라우트에서 사용
service = current_app.extensions['my_service']
```

## ANTI-PATTERNS

| ❌ 금지 | ✅ 대안 |
|---------|---------|
| `BlacklistService()` | ServiceFactory 등록 |
| `from services import X` | `current_app.extensions` |
| SQLAlchemy/Prisma | Raw SQL only |
| 서비스 간 직접 호출 | ServiceFactory 주입 |

## KNOWN ISSUES

| Issue | Severity |
|-------|----------|
| `blacklist_service.py` complexity 39.43 | HIGH |
| `cache_utils.py` complexity 42.01 | HIGH |
| DI violations: `admin_routes.py`, `fortimanager_push_service.py`, `settings_service.py` 직접 인스턴스 생성 | HIGH |
| `blacklist_service.py` 3 hardcoded URLs (L420, L462, L510) | CRITICAL |

## KEY FILES

| 파일 | Lines | 역할 |
|------|-------|------|
| `service_factory.py` | 400L | DI 컨테이너 |
| `blacklist_service.py` | 820L | IP 비즈니스 로직 ⚠️ |
| `database_service.py` | 300L | ThreadedConnectionPool |
