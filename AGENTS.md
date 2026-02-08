# AGENTS.md — Blacklist Intelligence Platform

**Generated:** 2026-02-08
**Commit:** 450d20c
**Branch:** master | **Version:** 3.5.39

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
```

```typescript
// API calls: ALWAYS through lib/api.ts
import { api } from '@/lib/api';
const data = await api.get('/blacklist');
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
| Unguarded `resp.json()` | `try/except` or status check | 10 violations exist |
| Cross-imports between services | DB, Redis, HTTP only | Service isolation |

## PROJECT STRUCTURE

```
app/                    # Flask API (Manual DI, Raw SQL)        :2542
collector/              # ETL Service (independent)             :8545
frontend/               # Next.js 15 Dashboard                  :2543
cloudflare/             # Cloudflare Workers edge API (D1+KV)
postgres/migrations/    # Raw SQL migrations (no ORM)
tests/                  # Pytest + Playwright
deploy/k8s/             # Kubernetes manifests
```

No cross-imports between app/, collector/, frontend/, cloudflare/. Communication: DB, Redis, HTTP only.

### Support Directories

| Directory | Purpose | Notes |
|-----------|---------|-------|
| `agent/` | AI agent (regtech_agent.py) | Experimental |
| `mock-fortigate/` | Flask mock server for testing | Test fixture |
| `docs/` | Deliverables, architecture diagrams | 9 deliverables + guides |
| `ssl/` | TLS certificates | **⚠ Private key committed — move to secrets** |
| `frontend-source/` | Stale `.next/` build artifacts | Should be gitignored |

## CI/CD

| Workflow | Trigger | Notes |
|----------|---------|-------|
| `release.yml` | Tag push `v*` | Builds 5 Docker images, creates airgap bundle |
| `ci.yml` | Push/PR | **Frontend only — NO backend tests in CI** |
| `ci-new.yml` | Migration | Replacement CI pipeline (in progress) |
| `release-new.yml` | Migration | Replacement release pipeline (in progress) |
| `airgap-build.yml` | Manual | Air-gap bundle creation |
| `build-images.yml` | Manual | Docker image builds |
| `run-tests.yml` | Manual | Test runner |

```bash
# Release: update VERSION → commit → tag → push
echo "X.Y.Z" > VERSION && git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin master vX.Y.Z  # GitHub Actions creates release
```

## SECURITY

- **JWT auth declared but NOT enforced** — no middleware validates tokens
- **⚠ SSL private key in `ssl/nxtd.co.kr.key`** — must move to secrets management
- Never log tokens, passwords, API keys
- Use `MOCK_CREDENTIALS` in tests (from `tests/test_config.py`)
- Secrets from env vars only; AES-256-GCM for stored credentials

## KNOWN ISSUES

### Hardcoded URLs (11 violations, 9 files) — CRITICAL

| File | Line(s) |
|------|---------|
| `app/core/routes/api/collection/utils.py` | 13 |
| `app/core/routes/api/blacklist/collection.py` | 54 |
| `app/core/services/blacklist_service.py` | 420, 462, 510 |
| `collector/fortimanager_uploader.py` | 36, 77 |
| `frontend/next.config.ts` | 7 |

Mixes `localhost:8545`, `blacklist-collector:8545`, `blacklist-app:443`. Fix: env vars (`COLLECTOR_URL`, `API_URL`).

### DI Violations (8 instances)

`admin_routes.py`, `fortimanager_push_service.py`, `settings_service.py` directly instantiate services instead of using `current_app.extensions`.

### Other

- Collector uses single-stage Dockerfile (includes Playwright bloat)
- Dashboard polls 30s + collection polls 5s simultaneously (dual polling)
- Three separate rate limiter instances (regtech, auth, Flask-Limiter)
- Dual ESLint configs: `eslint.config.mjs` (flat) + `.eslintrc.json` (legacy) — consolidate

## COMPLEXITY HOTSPOTS

| File | Complexity | Risk |
|------|-----------|------|
| `app/core/utils/cache_utils.py` | 42.01 | HIGH |
| `app/run_app.py` | 39.91 | HIGH |
| `app/core/services/blacklist_service.py` | 39.43 | HIGH |
| `collector/core/regtech_collector.py` | 961L | HIGH |
| `collector/core/multi_source_collector.py` | 766L | HIGH |
| `frontend/app/ip-management/IPManagementClient.tsx` | 893L | MEDIUM |

## RECENT CHANGES (v3.5.36 → v3.5.39)

- `ip_management_api.py` (1050L monolith) refactored → `app/core/routes/api/ip_management/` subpackage (repository.py, routes.py, handlers.py)
- `cloudflare/` Cloudflare Workers edge API added (D1 database, KV cache, 4 route modules)
- CI pipeline migration in progress (`ci-new.yml`, `release-new.yml`)

## NOTES

- SQLAlchemy in requirements.txt but **usage forbidden** — raw SQL only
- Legacy `app/core/collectors/` deleted — use `collector/` service
- Ruff(120) vs Prettier(100) — each applies to its own domain
- 14 services registered via ServiceFactory in strict lifecycle order (see `app/core/services/AGENTS.md`)
- `frontend-source/` contains stale build artifacts — do not use
