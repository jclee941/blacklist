# TESTS KNOWLEDGE BASE

**Generated:** 2026-02-11
**Commit:** 3f44350 | **Version:** 3.5.57
**Role:** Test Infrastructure & Patterns
**Parent:** [../AGENTS.md](../AGENTS.md)

## OVERVIEW

Multi-layer testing: Backend (pytest) + Frontend (Vitest/Playwright).
**Coverage target**: 80% on `app/core/`. **CI runs frontend tests only** — no backend tests in CI.

## STRUCTURE

```
tests/
├── unit/{app/,collector/,components/}   # Fast isolated tests
├── integration/{app/,collector/}        # Requires DB/Redis
├── e2e/                                 # Playwright
│   ├── homepage.spec.ts
│   ├── ip-management.spec.ts
│   ├── collection.spec.ts
│   ├── accessibility.spec.ts
│   ├── performance.spec.ts
│   └── visual-regression.spec.ts
└── test_config.py                       # MOCK_CREDENTIALS, fixtures
```

## COMMANDS

```bash
make test                    # All (backend + frontend)
make test-backend-unit       # Unit only
make test-backend-integration # With DB/Redis
make test-security           # @pytest.mark.security
make test-frontend           # Vitest
make test-frontend-e2e       # Playwright

# Single test
docker compose exec -T blacklist-app python -m pytest tests/unit -v -k "test_name"
cd frontend && npm run test -- --testNamePattern="test name"

# Update visual snapshots
cd frontend && npx playwright test --update-snapshots
```

## MARKERS (Backend)

| Marker | Purpose |
|--------|---------|
| `@pytest.mark.unit` | Fast, no external deps |
| `@pytest.mark.integration` | Requires DB/Redis |
| `@pytest.mark.security` | Auth/credential tests |
| `@pytest.mark.db` | Database operations |
| `@pytest.mark.api` | API endpoint tests |

## CONVENTIONS

| Convention | Rule |
|------------|------|
| File naming | `test_*.py` (backend), `*.test.tsx` (frontend) |
| Auth | Always `MOCK_CREDENTIALS` from `test_config.py` |
| Fixtures | `app`, `client`, `db_service`, `redis_client` (inline, no conftest.py) |
| Cleanup | Tests must clean up created data (use `yield` fixtures) |
| Visual | Multi-browser snapshots (Chromium, Firefox, Mobile Chrome) |

## ANTI-PATTERNS

| Forbidden | Alternative |
|-----------|-------------|
| Real credentials | `MOCK_CREDENTIALS` |
| `time.sleep()` | `pytest.mark.timeout` |
| Shared test state | Isolated fixtures |
| Skipping cleanup | `yield` fixtures |

## NOTES

- No `conftest.py` — fixtures defined inline in test files
- E2E timeout: 60s default, multi-browser (Chromium, Firefox, Mobile Chrome)
