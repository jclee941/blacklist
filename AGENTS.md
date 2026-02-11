# AGENTS.md — Blacklist Intelligence Platform

**Generated:** 2026-02-11
**Commit:** 2b9662f
**Branch:** master | **Version:** 3.5.59

## COMMANDS

```bash
# Development
make dev                    # All services (hot reload)
make dev-app / dev-frontend # API only / Frontend only

# Build & Deploy
make build                  # Production images (requires clean git tree)
make deploy                 # Deploy to production

# Testing
make test                   # All tests (backend + frontend)
make test-backend-unit      # Backend unit (pytest)
make test-backend-coverage  # Backend ≥80% coverage required
make test-frontend-unit     # Frontend unit (vitest)
make test-e2e               # E2E (Playwright: smoke/chromium/webkit)

# Single test
docker compose exec -T blacklist-app python -m pytest tests/unit -v -k "test_name"
cd frontend && npm run test -- --testNamePattern="test name"
# Misc: make db-shell / db-backup / db-restore / logs / clean
```

## CODE STYLE

| Domain | Formatter | Line | Indent | Quotes |
|--------|-----------|------|--------|--------|
| Python 3.11 | Ruff | 120 | 4 sp | Double `"` |
| TypeScript | Prettier | 100 | 2 sp | Single `'` |

- Type hints required (mypy strict). Semicolons required (TS).

## CRITICAL PATTERNS

### Python (Flask Backend)

```python
# DI: Access services via Flask extensions (MANDATORY)
blacklist_service = current_app.extensions['blacklist_service']

# Errors: RFC 7807 Problem Detail
raise APIError(status=400, code="INVALID_IP", message="Invalid IP format")
# Code prefixes: AUTH_, VALID_, NOT_FOUND_, INTERNAL_

# Public endpoints (no JWT)
from core.auth.decorators import public
@public
@bp.route("/health")
def health(): ...

# Logging
from core.logger import get_logger
logger = get_logger(__name__)
```

### TypeScript (Next.js Frontend)

```typescript
// API calls: ALWAYS through lib/api.ts (Bearer token auto-attached)
import { api } from '@/lib/api';
const data = await api.get('/blacklist');

// Auth via authApi
import { authApi } from '@/lib/api';
const { token } = await authApi.login(username, password);
```

## ANTI-PATTERNS (NEVER DO)

| Forbidden | Alternative | Reason |
|-----------|-------------|--------|
| `from app.core.services import X` | `current_app.extensions['x']` | Circular imports |
| `BlacklistService()` | ServiceFactory DI | Breaks injection |
| `fetch('localhost:2542')` | `api.get('/path')` | Env-dependent |
| SQLAlchemy / Prisma | Raw SQL only | Project policy |
| `as any`, `@ts-ignore` | Proper types | Type safety |
| Hardcoded ports/hosts | Environment variables | Deployment |
| Cross-imports between services | DB, Redis, HTTP only | Service isolation |
| Direct DB queries (frontend) | HTTP API calls | Security |

## PROJECT STRUCTURE

```
app/                    # Flask API (Manual DI, Raw SQL)        :2542
  core/auth/            # JWT (middleware, service, decorators)
  core/services/        # 14 services (ServiceFactory DI)
  routes/               # API endpoints (blueprints)
  migrations/           # Alembic SQL migrations
collector/              # ETL Service (independent)             :8545
  collectors/           # Data source adapters
frontend/               # Next.js 15 Dashboard                  :443
  app/                  # App Router pages
  lib/                  # Utilities (api.ts, hooks)
  e2e/                  # Playwright E2E tests (20 files)
postgres/migrations/    # Raw SQL migrations (no ORM)
tests/unit/             # Pytest: services/ (24), collector/ (11)
tests/mock-fortigate/   # Mock FortiManager API server
```

## WHERE TO LOOK

| Task | Directory | Child AGENTS.md |
|------|-----------|-----------------|
| Flask app init, blueprints | `app/` | `app/AGENTS.md` |
| Service lifecycle, DI | `app/core/services/` | `app/core/services/AGENTS.md` |
| JWT auth, @public | `app/core/auth/` | `app/core/auth/AGENTS.md` |
| REST API endpoints | `app/core/routes/api/` | `app/core/routes/api/AGENTS.md` |
| Collection mgmt API | `app/core/routes/api/collection/` | `app/core/routes/api/collection/AGENTS.md` |
| Web admin (Korean UI) | `app/core/routes/web/` | `app/core/routes/web/AGENTS.md` |
| Raw SQL, migrations | `app/core/database/` | `app/core/database/AGENTS.md` |
| Health, metrics | `app/core/monitoring/` | `app/core/monitoring/AGENTS.md` |
| Shared utilities | `app/core/utils/` | `app/core/utils/AGENTS.md` |
| Error handling, APIError | `app/core/exceptions/` | `app/core/exceptions/AGENTS.md` |
| ETL, data collection | `collector/` | `collector/AGENTS.md` |
| Collector core logic | `collector/core/` | `collector/core/AGENTS.md` |
| Next.js frontend | `frontend/` | `frontend/AGENTS.md` |
| Frontend libs, api.ts | `frontend/lib/` | `frontend/lib/AGENTS.md` |
| Backend tests, fixtures | `tests/` | `tests/AGENTS.md` |
| PostgreSQL schema | `postgres/` | `postgres/AGENTS.md` |

## ARCHITECTURE

| Service | Port | Healthcheck | Dependencies |
|---------|------|-------------|--------------|
| postgres | 5432 | `pg_isready` | None |
| redis | 6379 | `redis-cli ping` | None |
| collector | 8545 | `curl /health` | postgres, redis |
| app | 2542 | `curl /health` | postgres, redis, collector |
| frontend | 443 | `curl --insecure /health` | app |

- **CI:** push → detect-changes → lint/test (parallel) → build → e2e (smoke/chromium/webkit)
- **Release:** tag `v*` → validate VERSION==tag → build → airgap bundle → GitHub Release → GHCR
- **Deploy:** prod=manual airgap `docker load` | sandbox=Watchtower HTTP API auto-pull

## NOTES

- **Known:** DI violation in `fortimanager_push_service.py` — intentional standalone fallback
- **Known:** Auth middleware disabled — commented out at `app.py:156`, all endpoints public
- 14 services via ServiceFactory in strict lifecycle order (see `app/core/services/AGENTS.md`)
- `make build` requires clean git tree; backend coverage ≥80% enforced
- Complexity hotspots: `run_app.py` (39.91), `blacklist_service.py` (39.43)
- Korean UI in web admin panels; air-gap deployment via tarball bundles
