# Blacklist Platform - Testing Guide

| 항목 | 내용 |
|------|------|
| **버전** | 3.5.64 |
| **최종수정** | 2026-02-15 |
| **테스트 합계** | 992+ tests (151+ files) |

---

## Quick Reference

| Test Type | Framework | Files | Tests | Command | Time |
|-----------|-----------|-------|-------|---------|------|
| Backend Unit | Pytest | 107 | 785+ | `make test-backend-unit` | 1-2m |
| Frontend Unit | Vitest | 44 | 207+ | `make test-frontend-unit` | 30s |
| E2E | Playwright | 3+ | varies | `make test-e2e` | 5-10m |
| Backend Coverage | Pytest+cov | 107 | 785+ | `make test-backend-coverage` | 2-3m |
| **Total** | **Multiple** | **151+** | **992+** | **`make test`** | **10-15m** |

---

## Prerequisites

- **Docker**: All services run in containers
- **Make**: Build system (`make --version`)
- **Node.js**: 20+ (for frontend tests)
- **Python**: 3.11 (in container)

```bash
# Start all services (required for tests)
make dev
```

---

## Running Tests

### All Tests

```bash
# Run entire test suite (backend + frontend)
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
```
tests/
├── unit/
│   ├── auth/           # JWT, middleware tests (8 files)
│   ├── services/       # Service layer tests (14 files)
│   ├── routes/         # API endpoint tests (25+ files)
│   ├── database/       # Database layer tests
│   ├── utils/          # Utility tests
│   ├── collector/      # Collector unit tests
│   └── ...             # 107 files total
└── mock-fortigate/     # Mock FortiManager API server
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
```
frontend/
├── __tests__/          # 44 test files (207+ tests)
│   ├── components/     # Component tests
│   ├── hooks/          # Hook tests
│   ├── lib/            # Utility tests
│   └── app/            # Page tests
└── vitest.config.ts    # Vitest configuration
```

### E2E Tests (Playwright)

```bash
# Full E2E suite
make test-e2e

# Specific browser
cd frontend && npx playwright test --project=chromium
cd frontend && npx playwright test --project=webkit

# Headed mode (see browser)
cd frontend && npx playwright test --headed

# Debug mode
cd frontend && npx playwright test --debug
```

**Test locations:**
```
frontend/e2e/
├── smoke/              # Smoke tests (health, basic nav)
├── regression/         # Regression test suites
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

- Tests run against `https://localhost` (frontend with SSL)
- Chromium and WebKit browsers
- Smoke tests gate the full suite in CI

---

## CI/CD Integration

Tests run automatically via GitHub Actions (`ci.yml`):

```
Push/PR to master
  → detect-changes (what changed?)
  → lint-backend (Ruff) + lint-frontend (tsc)
  → test-backend (pytest) + test-frontend (vitest)    ← parallel
  → build (Docker images)
  → e2e-smoke → e2e-chromium → e2e-webkit             ← sequential
  → push-images (GHCR)
```

### Coverage Requirements

| Scope | Target | Tool |
|-------|--------|------|
| Backend (`app/core/`) | 80%+ | pytest-cov |
| Frontend | Tracked | Vitest coverage |

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

**문서 끝**
