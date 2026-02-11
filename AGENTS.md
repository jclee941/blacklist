# AGENTS.md — Blacklist Intelligence Platform

**Generated:** 2026-02-11
**Commit:** 6cd4c24
**Branch:** master | **Version:** 3.5.53

## COMMANDS

```bash
make dev                    # All services (hot reload)
make dev-app                # API only
make dev-frontend           # Frontend only
make test                   # All tests (backend + frontend)
make test-backend-unit      # Backend unit tests only
make test-backend-coverage  # Backend with coverage
make test-frontend          # Vitest
make test-frontend-e2e      # Playwright E2E
pre-commit run --all-files  # Ruff + mypy

# Single test
docker compose exec -T blacklist-app python -m pytest tests/unit -v -k "test_name"
cd frontend && npm run test -- --testNamePattern="test name"
```

## CODE STYLE

| Domain | Formatter | Line | Indent | Quotes |
|--------|-----------|------|--------|--------|
| Python 3.11 | Ruff | 120 | 4 sp | Double `"` |
| TypeScript | Prettier | 100 | 2 sp | Single `'` |

Type hints required (mypy). Semicolons required (TS). Import order: stdlib → third-party → first-party.
TS: `strict: true`, `noEmit`, `target: ES2020`, `bundler` moduleResolution, `@/*` path alias.

## CRITICAL PATTERNS

```python
# DI: Access services via Flask extensions (MANDATORY)
blacklist_service = current_app.extensions['blacklist_service']

# Errors: RFC 7807
raise APIError(status=400, code="INVALID_IP", message="Invalid IP format")
# Code prefixes: AUTH_, VALID_, NOT_FOUND_, INTERNAL_

# Auth: Mark public endpoints with @public decorator
from core.auth.decorators import public

@public  # No JWT required
@bp.route("/health")
def health(): ...
```

```typescript
// API calls: ALWAYS through lib/api.ts (Bearer token auto-attached)
import { api } from '@/lib/api';
const data = await api.get('/blacklist');

// Auth: login/logout/token via authApi
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

## PROJECT STRUCTURE

```
app/                    # Flask API (Manual DI, Raw SQL)        :2542
  core/auth/            # JWT authentication (middleware, service, decorators)
collector/              # ETL Service (independent)             :8545
frontend/               # Next.js 15 Dashboard                  :2543
postgres/migrations/    # Raw SQL migrations (no ORM)
tests/                  # Pytest + Playwright
```

No cross-imports between app/, collector/, frontend/. Communication: DB, Redis, HTTP only.

## AUTHENTICATION

JWT-based authentication via `app/core/auth/`:

| Component | File | Purpose |
|-----------|------|---------|
| JWTService | `jwt_service.py` | Token encode/decode (HS256, 8hr expiry) |
| Middleware | `middleware.py` | `before_request` hook — **CURRENTLY DISABLED** (commented out in `app.py:156`) |
| Decorators | `decorators.py` | `@public` — marks endpoint as no-auth-required |
| Routes | `routes/api/auth_routes.py` | POST `/api/auth/login`, GET `/me`, GET `/verify` |

**Public endpoints** (no JWT): `/health`, `/api/health`, `/metrics`, `/api/auth/login`, `/api/fortinet/threat-feed`, `/api/fortinet/json-connector`

Frontend sends Bearer token via Axios interceptor in `lib/api.ts`. On 401 → redirect to login.

## CI/CD

| Workflow | Trigger | Notes |
|----------|---------|-------|
| `ci.yml` | Push/PR to master | Path-filtered lint→test→Docker build→E2E (backend + frontend) |
| `release.yml` | Tag push `v*` | VERSION/tag validation→matrix Docker build→airgap→GH Release→GHCR |
| `deploy.yml` | Release completion / manual | Airgap deploy to self-hosted runner (`/opt/blacklist/`) |
| `build-images.yml` | Manual | Docker image builds |
| `run-tests.yml` | Manual | Test runner |

```bash
# Release: update VERSION → commit → tag → push
echo "X.Y.Z" > VERSION && git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin master vX.Y.Z  # GitHub Actions creates release
```

## SECURITY

- **JWT auth enforced** on all API routes via `before_request` middleware (`app/core/auth/`)
- SSL private key removed from Git history; certificates in `.gitignore`
- Never log tokens, passwords, API keys
- Use `MOCK_CREDENTIALS` in tests (from `tests/test_config.py`)
- Secrets from env vars only; AES-256-GCM for stored credentials

## KNOWN ISSUES

### DI Violations (1 active instance) — Intentional

`fortimanager_push_service.py` directly instantiates services. This is intentional fallback for standalone execution outside Flask context.

## COMPLEXITY HOTSPOTS

| File | Complexity | Risk |
|------|-----------|------|
| `app/run_app.py` | 39.91 | HIGH |
| `app/core/services/blacklist_service.py` | 39.43 | HIGH |

## NOTES

- SQLAlchemy in requirements.txt but **usage forbidden** — raw SQL only
- Ruff(120) vs Prettier(100) — each applies to its own domain
- 14 services registered via ServiceFactory in strict lifecycle order (see `app/core/services/AGENTS.md`)
