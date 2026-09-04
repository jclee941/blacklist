# Blacklist Platform - Testing Guide

| 항목         | 내용                                                                |
| ------------ | ------------------------------------------------------------------- |
| **버전**     | 4.1.0                                                               |
| **최종수정** | 2026-07-29                                                          |
| **범위**     | Backend/collector Pytest, frontend Vitest, and Playwright scenarios |

---

## Quick Reference

| Test Type              | Framework    | Location                                     | Command                         | Notes                                                                |
| ---------------------- | ------------ | -------------------------------------------- | ------------------------------- | -------------------------------------------------------------------- |
| Backend Unit           | Pytest       | `tests/unit/` except `tests/unit/collector/` | `make test-backend-unit`        | Enforces 80% app coverage                                            |
| Collector Unit         | Pytest       | `tests/unit/collector/`                      | `make test-collector-unit`      | Uses the isolated collector import path                              |
| Backend Integration    | Pytest       | `tests/integration/`                         | `make test-backend-integration` | Credential persistence scenarios                                     |
| Frontend Unit          | Vitest       | `frontend/__tests__/`                        | `make test-frontend-unit`       | Runs Vitest once                                                     |
| E2E                    | Playwright   | `frontend/e2e/`                              | `make test-frontend-e2e`        | Separate from `make test`; CI budget is 60 minutes                   |
| Backend Coverage       | Pytest+cov   | application unit suite                       | `make test-backend-coverage`    | Writes terminal, HTML, and XML reports                               |
| **Unit + integration** | **Multiple** | **repository**                               | **`make test`**                 | **Backend, collector, integration, and Vitest; excludes Playwright** |

---

## Prerequisites

- **Docker**: All services run in containers
- **Make**: Build system (`make --version`)
- **Node.js**: 24 (for frontend tests)
- **Python**: 3.11 (in container)

```bash
# Start all services when running browser E2E scenarios
make dev
```

---

## Running Tests

### All Tests

```bash
# Run backend, collector, integration, and frontend unit suites
# Playwright E2E runs separately.
make test
```

### Backend Unit Tests (Pytest)

```bash
# All backend tests
make test-backend-unit

# With coverage report (80% minimum enforced)
make test-backend-coverage

# Single test file
docker compose exec -T blacklist-app python -m pytest tests/unit -v -k "test_name"

# Specific test directory
docker compose exec -T blacklist-app python -m pytest tests/unit/services/ -v

# Run with verbose output
docker compose exec -T blacklist-app python -m pytest tests/unit -v --tb=short
```

**Test locations:**

```text
tests/
├── unit/
│   ├── auth/           # JWT and middleware tests
│   ├── services/       # Service layer tests
│   ├── routes/         # API endpoint tests
│   ├── common/         # Configuration tests
│   ├── errors/         # Error-handler tests
│   ├── monitoring/     # Metrics tests
│   ├── utils/          # Utility tests
│   ├── collector/      # Collector unit tests
│   └── ...             # Other focused unit-test domains
```

### Frontend Unit Tests (Vitest)

```bash
# All frontend tests
make test-frontend-unit

# Or directly via npm
cd frontend && npm run test

# Specific test
cd frontend && npm run test -- --testNamePattern="test name"

# Watch mode
cd frontend && npm run test -- --watch
```

**Test locations:**

```text
frontend/
├── __tests__/          # Vitest unit tests
│   ├── clients/        # Client component tests
│   ├── components/     # Component tests
│   ├── hooks/          # Hook tests
│   ├── lib/            # Utility tests
│   └── pages/          # Page tests
└── vitest.config.ts    # Vitest configuration
```

### E2E Tests (Playwright)

```bash
# Full E2E suite
E2E_USERNAME=admin E2E_PASSWORD='<test-password>' make test-frontend-e2e

# Specific browser
cd frontend && npx playwright test --project=chromium
cd frontend && WEBKIT_ENABLED=true npx playwright test --project=webkit

# Headed mode (see browser)
cd frontend && npx playwright test --headed

# Debug mode
cd frontend && npx playwright test --debug
```

**Test locations:**

```text
frontend/
├── e2e/                # Feature, smoke, regression, and visual scenarios
└── playwright.config.ts
```

---

## Test Architecture

### Backend (Pytest)

- **No `conftest.py`** — fixtures defined inline in each test file
- **No ORM** — raw SQL only, mocked at database layer
- **DI pattern** — services accessed via `current_app.extensions['service_name']`
- **RFC 7807** — error responses follow Problem Detail format

```python
# Example: typical backend unit test pattern
def test_get_blacklist_returns_data(app, mock_db):
    """Test blacklist retrieval."""
    with app.app_context():
        service = app.extensions["blacklist_service"]
        result = service.get_all()
        assert isinstance(result, list)
```

### Frontend (Vitest)

- **React Testing Library** for component tests
- **Path aliases** — `@/` maps to project root
- **No `as any`** — strict TypeScript enforced
- **API mocking** — `lib/api.ts` calls mocked, never real HTTP

```typescript
// Example: typical frontend unit test pattern
import { render, screen } from '@testing-library/react';
import { Dashboard } from '@/components/Dashboard';

describe('Dashboard', () => {
  it('renders loading state', () => {
    render(<Dashboard />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
});
```

### E2E (Playwright)

- CI tests run against `https://localhost:3443` through the frontend proxy.
- Chromium runs by default; WebKit requires `WEBKIT_ENABLED=true` and is enabled in CI.
- The E2E job runs the configured browser matrix as one workflow job.

---

## CI/CD Integration

Tests run automatically via GitHub Actions (`ci.yml`):

```text
Push/PR to master
  → detect-changes (what changed?)
  → lint-backend (Ruff) + lint-frontend (tsc)
  → test-backend (pytest) + test-frontend (vitest)    ← parallel
  → build (Docker images)
  → build (Docker images) → e2e + image scans
  → ci-gate (aggregate internal CI result)
  → push-images (GHCR, master only)
```

### Coverage Requirements

| Scope                 | Target  | Tool            |
| --------------------- | ------- | --------------- |
| Backend (`app/core/`) | 80%+    | pytest-cov      |
| Frontend              | Tracked | Vitest coverage |

Coverage below 80% on backend **fails the CI pipeline**.

---

## Common Issues

### 1. "Container not running"

```bash
# Ensure services are up
make dev
# Or for tests specifically
docker compose up -d blacklist-app blacklist-postgres blacklist-redis
```

### 2. "Database connection refused"

```bash
# Check postgres health
docker compose exec blacklist-postgres pg_isready
# Restart if needed
docker compose restart blacklist-postgres
```

### 3. "Playwright browsers not installed"

```bash
cd frontend && npx playwright install
```

### 4. Frontend type errors blocking tests

```bash
# Check types first
cd frontend && npx tsc --noEmit
# Then run tests
cd frontend && npm run test
```

---

## Adding New Tests

### Backend

1. Create test file in `tests/unit/<category>/test_<name>.py`
2. Define fixtures inline (no conftest.py)
3. Mock services via `current_app.extensions`
4. Run: `docker compose exec -T blacklist-app python -m pytest tests/unit -v -k "test_name"`

### Frontend

1. Create test file in `frontend/__tests__/<category>/<name>.test.tsx`
2. Use React Testing Library + Vitest
3. Mock API calls from `@/lib/api`
4. Run: `cd frontend && npm run test -- --testNamePattern="test name"`

---

## See Also

- [`AGENTS.md`](../../AGENTS.md) — Development rules and patterns
- [`frontend/AGENTS.md`](../../frontend/AGENTS.md) — Frontend testing conventions
- [`tests/AGENTS.md`](../../tests/AGENTS.md) — Backend test fixtures and patterns
- [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) — CI pipeline definition

---

## 문서 끝
