# AGENTS.md — Blacklist Intelligence Platform

**Generated:** 2026-02-11
**Commit:** f082182
**Branch:** master | **Version:** 3.5.57

## COMMANDS

### Development

```bash
make dev                    # All services (hot reload)
make dev-no-build           # Dev without docker build (reuse existing images)
make dev-prod               # Dev with production configuration
make dev-app                # API only (Flask debug mode)
make dev-frontend           # Frontend only (webpack dev server)
```

### Build & Deployment

```bash
make build                  # Build production images (requires clean git working tree)
make rebuild                # Force rebuild without cache
make ci-build               # Build with CI optimizations
make deploy                 # Deploy to production (self-hosted runner)
```

### Testing

```bash
make test                   # All tests (backend + frontend)
make test-backend-unit      # Backend unit tests only (pytest)
make test-backend-coverage  # Backend with coverage report (≥80% required)
make test-frontend-unit     # Frontend unit tests (vitest)
make test-collector         # Collector service tests
make test-smoke             # Smoke tests (basic health checks)
make test-e2e               # E2E tests (Playwright)
make test-ci                # Tests with CI configuration

# Single test
docker compose exec -T blacklist-app python -m pytest tests/unit -v -k "test_name"
cd frontend && npm run test -- --testNamePattern="test name"
```

### Service Management

```bash
make up                     # Start all services
make down                   # Stop all services
make restart                # Restart all services
make prod                   # Production environment setup
```

### Monitoring & Debugging

```bash
make logs                   # All service logs (streaming)
make logs-app               # Flask app logs
make logs-frontend          # Frontend logs
make logs-collector         # Collector logs
make logs-postgres          # PostgreSQL logs
make logs-redis             # Redis logs
make health                 # Health check status
make status                 # Service status summary
make info                   # System information
```

### Database

```bash
make db-shell               # Interactive PostgreSQL shell
make db-backup              # Backup database to ./data/backups/
make db-restore             # Restore from latest backup
```

### Maintenance

```bash
make clean                  # Remove containers and volumes (keep data)
make clean-all              # Remove everything including images
make setup-hooks            # Setup git hooks (pre-commit)
```

## CODE STYLE

| Domain | Formatter | Line | Indent | Quotes |
|--------|-----------|------|--------|--------|
| Python 3.11 | Ruff | 120 | 4 sp | Double `"` |
| TypeScript | Prettier | 100 | 2 sp | Single `'` |

**Requirements:**
- Type hints required (mypy strict mode)
- Semicolons required (TypeScript)
- Import order: stdlib → third-party → first-party
- TS: `strict: true`, `noEmit`, `target: ES2020`, `bundler` moduleResolution, `@/*` path alias

## CRITICAL PATTERNS

### Python (Flask Backend)

```python
# DI: Access services via Flask extensions (MANDATORY)
blacklist_service = current_app.extensions['blacklist_service']

# Errors: RFC 7807 Problem Detail
raise APIError(status=400, code="INVALID_IP", message="Invalid IP format")
# Code prefixes: AUTH_, VALID_, NOT_FOUND_, INTERNAL_

# Auth: Mark public endpoints with @public decorator
from core.auth.decorators import public

@public  # No JWT required
@bp.route("/health")
def health(): ...

# Logging
from core.logger import get_logger
logger = get_logger(__name__)
logger.info("Message", extra={"context": "value"})
```

### TypeScript (Next.js Frontend)

```typescript
// API calls: ALWAYS through lib/api.ts (Bearer token auto-attached)
import { api } from '@/lib/api';
const data = await api.get('/blacklist');

// Auth: login/logout/token via authApi
import { authApi } from '@/lib/api';
const { token } = await authApi.login(username, password);

// Components: Use TypeScript interfaces, no 'any'
interface Props {
  items: Item[];
  onSelect: (id: string) => void;
}

export function MyComponent({ items, onSelect }: Props) {
  // implementation
}
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
| Direct database queries (frontend) | HTTP API calls | Security & separation |

## PROJECT STRUCTURE

```
app/                    # Flask API (Manual DI, Raw SQL)        :2542
  core/
    auth/               # JWT authentication (middleware, service, decorators)
    services/           # 14 services (ServiceFactory DI)
  routes/               # API endpoints (blueprints)
  migrations/           # Alembic SQL migrations

collector/              # ETL Service (independent)             :8545
  collectors/           # Data source adapters
  services/             # Collector logic
  
frontend/               # Next.js 15 Dashboard                  :2543
  app/                  # Next.js App Router
  components/           # React components
  lib/                  # Utilities (api.ts, hooks, etc.)
  __tests__/            # Vitest unit tests
  e2e/                  # Playwright E2E tests

postgres/
  migrations/           # Raw SQL migrations (no ORM)

tests/                  # Pytest unit tests
  unit/
    services/           # 24 service test files
    collector/          # 11 collector test files
  conftest.py           # Pytest fixtures & shared setup
  mock-fortigate/       # Mock API server
```

**Key Rule:** No cross-imports between `app/`, `collector/`, `frontend/`. Communication: DB, Redis, HTTP only.

## BUILD SYSTEM (Makefile)

### Target Categories (50+)

| Category | Targets | Purpose |
|----------|---------|---------|
| **Development** | dev, dev-no-build, dev-prod, dev-app, dev-frontend | Start local development environment with hot reload |
| **Service Management** | up, down, restart, prod | Control Docker Compose services |
| **Build & Deploy** | build, rebuild, ci-build, deploy | Build production images, deploy to production |
| **Testing** | test, test-backend-*, test-frontend-*, test-collector, test-smoke, test-ci, test-e2e | Run all test suites |
| **Database** | db-shell, db-backup, db-restore | PostgreSQL management |
| **Monitoring** | logs, logs-*, health, status, info | View logs, health checks, system info |
| **Maintenance** | clean, clean-all, setup-hooks | Cleanup and git hooks |

### Key Constraints

**C1: Git Working Tree Must Be Clean**
```bash
make build  # Requires: git diff-index --quiet HEAD
```
Any uncommitted changes will fail the build. Reason: Ensures reproducible builds tied to specific commits.

**C2: Coverage Threshold**
```bash
make test-backend-coverage  # Requires: ≥80% coverage
```
Backend unit tests must have at least 80% code coverage or build fails.

## DOCKER COMPOSE ARCHITECTURE

### 5-Service Stack

```yaml
# docker-compose.yml
version: '3.8'

services:
  blacklist-postgres:
    image: postgres:16
    ports: [5432:5432]
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: blacklist
      POSTGRES_USER: postgres

  blacklist-redis:
    image: redis:7
    ports: [6379:6379]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    volumes:
      - ./data/redis:/data

  blacklist-collector:
    build:
      context: ./services/collector
      dockerfile: Dockerfile
      args:
        GIT_COMMIT: ${GIT_COMMIT:-unknown}
    ports: [8545:8545]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8545/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    environment:
      - RPC_ENDPOINT=${RPC_ENDPOINT}
      - WEB3_PROVIDER_URI=${WEB3_PROVIDER_URI}

  blacklist-app:
    build:
      context: ./services/app
      dockerfile: Dockerfile
      args:
        GIT_COMMIT: ${GIT_COMMIT:-unknown}
    ports: [2542:2542]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2542/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s
    environment:
      - FLASK_ENV=${FLASK_ENV}
      - POSTGRES_DSN=${POSTGRES_DSN}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - blacklist-postgres
      - blacklist-redis
      - blacklist-collector

  blacklist-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        GIT_COMMIT: ${GIT_COMMIT:-unknown}
    ports: [443:443]
    healthcheck:
      test: ["CMD", "curl", "-f", "--insecure", "https://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    volumes:
      - ./frontend:/app  # Development bind mount
```

### Service Details

| Service | Port | Healthcheck | Start Period | Dependencies |
|---------|------|-------------|--------------|--------------|
| **postgres** | 5432 | `pg_isready` | 30s | None |
| **redis** | 6379 | `redis-cli ping` | 30s | None |
| **collector** | 8545 | `curl /health` | 60s | postgres, redis |
| **app** | 2542 | `curl /health` | 90s | postgres, redis, collector |
| **frontend** | 443 | `curl --insecure /health` | 60s | app |

### GIT_COMMIT Injection

All services inject build-time commit hash via `GIT_COMMIT` build arg:

```yaml
args:
  GIT_COMMIT: ${GIT_COMMIT:-unknown}
```

This allows tracking which commit produced which Docker image. Set during CI/CD:
```bash
docker-compose build --build-arg GIT_COMMIT=$(git rev-parse --short HEAD)
```

## CI/CD WORKFLOWS

### 6 GitHub Actions Workflows

#### 1. ci.yml — Main CI Pipeline

**Trigger:** Push to any branch  
**Concurrency:** Only 1 CI per branch (newer push cancels previous)

**Job Chain:**
```
detect-changes (detect modified paths)
├─ lint-frontend (if frontend/* changed)
│  └─ test-frontend (vitest with jsdom)
├─ lint-backend (if app/* changed)
│  └─ test-backend (pytest with ≥80% coverage)
├─ lint-collector (if collector/* changed)
│  └─ test-collector (pytest)
└─ build (all lint/test pass)
   └─ e2e (if build succeeds)
      ├─ smoke (single test, Chrome)
      ├─ chromium (full e2e suite)
      └─ webkit (full e2e suite)
```

**Key Features:**
- Path-based filtering (only run tests for changed services)
- Parallel lint + test execution
- Sequential build (requires all tests pass)
- E2E only runs if build succeeds
- Concurrency cancellation (cancel-in-progress: true)

#### 2. release.yml — Automated Release

**Trigger:** Tag push matching `v*` pattern  
**Example:** Push `v3.5.57` tag

**Job Chain:**
```
validate-version
├─ Extract VERSION from VERSION file (3.5.57)
├─ Extract TAG_VERSION from git tag (v3.5.57 → 3.5.57)
└─ Exit if VERSION ≠ TAG_VERSION

build-images (matrix: postgres, redis, collector, app, frontend)
├─ docker build -t ghcr.io/blacklist-dev/[service]:v3.5.57
└─ docker build -t ghcr.io/blacklist-dev/[service]:latest

package-airgap
├─ docker save ghcr.io/blacklist-dev/postgres:v3.5.57 > postgres.tar
├─ docker save ghcr.io/blacklist-dev/redis:v3.5.57 > redis.tar
├─ ... (all 5 services)
└─ tar -czf blacklist-v3.5.57-airgap.tar.gz *.tar

create-release
├─ Create GitHub Release with airgap bundle as asset
└─ Tag: v3.5.57, Release body: auto-generated

push-registry
└─ docker push ghcr.io/blacklist-dev/* (all services, all tags)
```

**Constraints:**
- VERSION file must exactly match tag value (no 'v' prefix)
- Example: tag `v3.5.57` requires VERSION file to contain `3.5.57`

#### 3. deploy.yml — Production Deployment

**Trigger:** Manual (workflow_dispatch) + branch filter  
**Target:** Self-hosted runner at `/opt/blacklist/` (production server)

**Job Chain:**
```
download-bundle
├─ Fetch airgap bundle from GitHub release assets
└─ Extract: tar -xzf blacklist-v3.5.57-airgap.tar.gz

preserve-data
├─ mkdir -p /tmp/backup
└─ cp -r /opt/blacklist/data/* /tmp/backup/

load-images
├─ docker load < postgres.tar
├─ docker load < redis.tar
├─ docker load < collector.tar
├─ docker load < app.tar
└─ docker load < frontend.tar

start-services
├─ cd /opt/blacklist
└─ docker-compose up -d

restore-data
├─ cp /tmp/backup/* /opt/blacklist/data/
└─ Ensures data persists across deployments

health-checks (retry 3 times, 30s interval)
├─ curl http://localhost:2542/health (app)
├─ curl https://localhost/health (frontend)
├─ ... (all 5 services)
└─ Exit if any health check fails
```

**Key Features:**
- Data preservation (backup before, restore after)
- Health checks with retries (3 retries, 30s interval)
- Airgap-first (no network pull, all images bundled)

#### 4. deploy-sandbox.yml — Sandbox Deployment

**Trigger:** Manual (workflow_dispatch)  
**Target:** SSH to 192.168.50.220 (sandbox VM)

**Job Chain:**
```
deploy-to-vm
├─ SSH to 192.168.50.220
├─ docker pull ghcr.io/blacklist-dev/postgres:latest
├─ docker pull ghcr.io/blacklist-dev/redis:latest
├─ docker pull ghcr.io/blacklist-dev/collector:latest
├─ docker pull ghcr.io/blacklist-dev/app:latest
└─ docker pull ghcr.io/blacklist-dev/frontend:latest

start-services
├─ cd /path/to/sandbox
└─ docker-compose up -d

health-checks
└─ Retry 3 times, 30s interval per service
```

**Pattern:** GHCR pull (internet-required, faster than airgap)

#### 5. build-images.yml — Manual Image Builder

**Trigger:** Manual (workflow_dispatch)  
**Inputs:** 
- service (optional, default: all)
- push_to_registry (optional, default: false)

**Job Chain:**
```
build-matrix (services: postgres, redis, collector, app, frontend)
├─ docker build -t ghcr.io/blacklist-dev/[service]:dev
└─ Optional: docker push ghcr.io/blacklist-dev/[service]:dev
```

**Use Case:** Quick image rebuild for testing, optional GHCR push

#### 6. run-tests.yml — Manual Test Runner

**Trigger:** Manual (workflow_dispatch)

**Job Chain (parallel):**
```
test-backend-unit
├─ pytest tests/unit/services/* (24 files)
├─ pytest tests/unit/collector/* (11 files)
└─ Coverage: ≥80% required

test-frontend-unit
├─ vitest frontend/__tests__/*
└─ jsdom environment

test-collector
└─ pytest tests/unit/collector/*
```

### CI/CD Constraints

**C3: E2E Single-Worker in CI**
```typescript
// frontend/playwright.config.ts
workers: process.env.CI ? 1 : undefined
```
E2E tests run single-worker (sequential) in CI to prevent flakiness. Local development can run tests in parallel.

**C4: Backend Coverage ≥80%**
```ini
# pyproject.toml
--cov-fail-under=80
```
Backend test coverage must be at least 80% or build fails.

**C5: Concurrency Cancellation**
```yaml
# ci.yml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```
Only one CI run per branch. Newer push cancels previous run.

## TEST STRUCTURE & PATTERNS

### Pytest (Backend Unit Tests)

**Config:** `pyproject.toml`  
**Framework:** pytest with coverage plugin

```ini
[tool.pytest.ini_options]
markers = [
    "service: mark test as service test",
    "collector: mark test as collector test", 
    "smoke: mark test as smoke test",
]
addopts = "--cov=app --cov=collector --cov-fail-under=80"
testpaths = ["tests/unit"]
```

**Test Paths:**
- `tests/unit/services/*.py` — 24 backend service tests
- `tests/unit/collector/*.py` — 11 collector service tests

**Run Locally:**
```bash
make test-backend-unit          # All backend tests
make test-backend-coverage      # With coverage report
pytest tests/unit -v -k "test_name"  # Single test
```

**Run in CI:**
```bash
pytest tests/unit --cov --cov-fail-under=80
```

### Vitest (Frontend Unit Tests)

**Config:** `frontend/vitest.config.ts`  
**Environment:** jsdom (browser-like DOM)

```typescript
export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    coverage: {
      provider: "v8",
      include: ["src/**"],
      exclude: ["**/*.test.ts", "**/index.ts"],
    },
  },
})
```

**Test Pattern:** `frontend/__tests__/**/*.test.ts`

**Run Locally:**
```bash
make test-frontend-unit         # All frontend tests
cd frontend && npm run test     # Or directly
```

**Run in CI:**
```bash
cd frontend && npm run test -- --coverage
```

### Playwright (E2E Tests)

**Config:** `frontend/playwright.config.ts`  
**Projects:** smoke, chromium, webkit

```typescript
export default defineConfig({
  testDir: "./e2e",
  timeout: 60 * 1000,  // 60 seconds per test
  workers: process.env.CI ? 1 : undefined,  // 1 in CI, parallel locally
  projects: [
    { name: "smoke", testMatch: "**/smoke.spec.ts" },
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
})
```

**Test Pattern:** `frontend/e2e/**/*.spec.ts` (20 test files)

**E2E Test Files:**
```
frontend/e2e/
├── smoke.spec.ts               # Smoke tests (fast validation)
├── features/
│   ├── authentication.spec.ts
│   ├── dashboard.spec.ts
│   └── ...
├── core/
│   ├── api-integration.spec.ts
│   └── ...
├── quality/
│   ├── performance.spec.ts
│   └── ...
├── error-handling/
│   ├── error-pages.spec.ts
│   └── ...
└── regression/
    └── previous-bugs.spec.ts
```

**Run Locally:**
```bash
make test-e2e                   # All E2E tests
npx playwright test             # Or directly
npx playwright test --project=smoke  # Single project
```

**Run in CI:**
```bash
# Runs all 3 projects (smoke, chromium, webkit) sequentially
CI=true npx playwright test
```

### Test Fixtures & Patterns

**Location:** `tests/conftest.py`

Common patterns:
```python
@pytest.fixture
def mock_service():
    """Mock blacklist service"""
    with patch('app.core.services.blacklist_service') as mock:
        yield mock

@pytest.mark.service
def test_blacklist_service(mock_service):
    """Test service behavior"""
    assert mock_service.called

@pytest.mark.parametrize("input,expected", [
    ("192.168.1.1", True),
    ("invalid", False),
])
def test_ip_validation(input, expected):
    """Test IP validation with multiple inputs"""
    assert validate_ip(input) == expected
```

**Run with specific marker:**
```bash
pytest tests/unit -m service       # Only @pytest.mark.service tests
pytest tests/unit -m collector     # Only @pytest.mark.collector tests
```

## RELEASE PROCESS

### Release Checklist

1. **Update VERSION file**
   ```bash
   echo "3.5.58" > VERSION
   git add VERSION
   git commit -m "Bump version to 3.5.58"
   ```

2. **Create git tag** (must match VERSION)
   ```bash
   git tag -a v3.5.58 -m "Release v3.5.58"
   ```

3. **Push both commit and tag**
   ```bash
   git push origin master v3.5.58
   ```

4. **Automated steps (GitHub Actions):**
   - ✅ release.yml validates VERSION == tag
   - ✅ Builds all 5 service images
   - ✅ Tags images as `ghcr.io/blacklist-dev/[service]:v3.5.58`
   - ✅ Creates airgap bundle (`blacklist-v3.5.58-airgap.tar.gz`)
   - ✅ Creates GitHub Release with bundle as asset
   - ✅ Pushes all images to GHCR (ghcr.io/blacklist-dev/*)

### Constraint: VERSION = TAG

**Example:**
```
VERSION file: 3.5.58
Git tag:     v3.5.58  ← Release fails if mismatch
```

The tag prefix 'v' is stripped when comparing with VERSION file.

## DEPLOYMENT PATTERNS

### Production (Air-Gap First)

**Environment:** Self-hosted runner at `/opt/blacklist/`  
**Trigger:** Manual GitHub Actions deployment  
**Network:** Air-gapped (no external image pulls)

**Flow:**
1. Download airgap bundle from GitHub release assets
2. Extract Docker images locally (`docker load`)
3. Backup existing data (`/opt/blacklist/data/`)
4. Start new containers with loaded images
5. Restore data to new containers
6. Health checks with retries

**Constraints:**
- **C6: Data Must Be Preserved**
  All data in `/opt/blacklist/data/*` is backed up before deployment and restored afterward.
- All 5 services must pass health checks before deployment succeeds

### Sandbox (GHCR Pull)

**Environment:** SSH to 192.168.50.220 (staging VM)  
**Trigger:** Manual GitHub Actions deployment  
**Network:** Internet-required (pulls from GHCR)

**Flow:**
1. SSH to sandbox VM (192.168.50.220)
2. Pull latest images from GHCR
3. Start containers with pulled images
4. Health checks with retries

### Development (Hot Reload)

**Environment:** Local machine or dev container  
**Trigger:** `make dev`  
**Network:** Full Docker Compose with bind mounts

**Flow:**
1. Build images from Dockerfiles
2. Start all services with `docker-compose up -d`
3. Bind mount `/app` directory (both frontend and backend)
4. Frontend watches for changes (webpack dev server)
5. Backend reloads on changes (Flask debug mode)
6. Persistent data in `./data/` volumes

**Advantages:**
- Instant hot reload (no rebuild)
- Full debugging (breakpoints, logs)
- Close to production environment

## AUTHENTICATION

JWT-based authentication via `app/core/auth/`:

| Component | File | Purpose |
|-----------|------|---------|
| JWTService | `jwt_service.py` | Token encode/decode (HS256, 8hr expiry) |
| Middleware | `middleware.py` | `before_request` hook — **CURRENTLY DISABLED** (commented out in `app.py:156`) |
| Decorators | `decorators.py` | `@public` — marks endpoint as no-auth-required |
| Routes | `routes/api/auth_routes.py` | POST `/api/auth/login`, GET `/me`, GET `/verify` |

**Public endpoints** (no JWT required):
- `/health`
- `/api/health`
- `/metrics`
- `/api/auth/login`
- `/api/fortinet/threat-feed`
- `/api/fortinet/json-connector`

**Protected endpoints** (JWT required):
- All other `/api/*` routes

**Frontend Flow:**
1. User submits login form
2. Frontend calls `authApi.login(username, password)`
3. Backend returns JWT token
4. Frontend stores token in localStorage
5. Axios interceptor in `lib/api.ts` attaches Bearer token to all requests
6. On 401 response → redirect to login page

## SECURITY

- **JWT auth enforced** on all API routes via `before_request` middleware (`app/core/auth/`)
- SSL private key removed from Git history; certificates in `.gitignore`
- Never log tokens, passwords, API keys
- Use `MOCK_CREDENTIALS` in tests (from `tests/test_config.py`)
- Secrets from env vars only; AES-256-GCM for stored credentials
- CORS configured for frontend domain only

## ENVIRONMENT VARIABLES

| Variable | Type | Where Used | Default | Required |
|----------|------|-----------|---------|----------|
| GIT_COMMIT | string | All service Docker builds | "unknown" | No |
| FLASK_ENV | string | blacklist-app | "development" | Yes (prod) |
| POSTGRES_DSN | string | blacklist-app | None | Yes |
| REDIS_URL | string | blacklist-app | None | Yes |
| RPC_ENDPOINT | string | blacklist-collector | None | Yes |
| WEB3_PROVIDER_URI | string | blacklist-collector | None | Yes |
| REGTECH_API_KEY | string | blacklist-collector | None | Yes (prod) |

See `.env.example` for complete list with descriptions.

## KNOWN ISSUES

### DI Violations (1 active instance) — Intentional

`fortimanager_push_service.py` directly instantiates services. This is intentional fallback for standalone execution outside Flask context.

### Auth Middleware Currently Disabled

JWT authentication middleware is commented out in `app.py:156`. All endpoints are currently public. This should be re-enabled when frontend authentication is implemented.

## COMPLEXITY HOTSPOTS

| File | Complexity | Risk | Notes |
|------|-----------|------|-------|
| `app/run_app.py` | 39.91 | HIGH | App initialization, service registration |
| `app/core/services/blacklist_service.py` | 39.43 | HIGH | Core business logic, IP validation, filtering |

## NOTES

- SQLAlchemy in requirements.txt but **usage forbidden** — raw SQL only
- Ruff (120 line length) applies to Python; Prettier (100) applies to TypeScript
- 14 services registered via ServiceFactory in strict lifecycle order (see `app/core/services/AGENTS.md`)
- Middleware is disabled by default (line 156 in `app.py` is commented)
- All Docker images use Debian-based (not Alpine) for debugging compatibility
