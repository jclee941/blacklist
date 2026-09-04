# TESTS KNOWLEDGE BASE

## OVERVIEW

Multi-layer testing: pytest (backend) + Vitest (frontend unit) + Playwright (E2E). Coverage target: 80% on `app/core/`.

## STRUCTURE

```text
tests/
├── unit/
│   ├── test_*.py      # installer, deploy, release, workflow-contract tests
│   ├── routes/       # Flask route tests
│   ├── services/     # application service tests
│   ├── collector/    # isolated collector tests
│   ├── utils/        # shared utility tests
│   ├── auth/         # JWT and middleware tests
│   ├── monitoring/   # metrics tests
│   ├── common/       # configuration tests
│   └── errors/       # error-handler tests
└── integration/      # credential persistence integration tests
```

## CONFIG

- `pyproject.toml`: 5 markers (`unit`, `integration`, `security`, `db`, `api`).
- Default `pytest tests/unit` **ignores `tests/unit/collector`** (`addopts`); run collector tests via `make test-collector-unit` (`PYTHONPATH=collector`, `-o 'pythonpath=["collector"]'`).
- No `conftest.py` — inline fixtures with `yield` cleanup.
- Coverage: `--cov-fail-under=80`.
- Shared case-data modules (no tests inside): `unit/services/blacklist_service_extended_cases.py`, `frontend/__tests__/lib/api-*.cases.ts`.

## CONVENTIONS

- File naming: `test_*.py` (pytest), `*.test.tsx` (Vitest), `*.spec.ts` (Playwright).
- Playwright tests live in `frontend/e2e/` and use Chromium plus optional WebKit.
- E2E regression format: `issue-{NUMBER}-{description}.spec.ts` with `PROBLEM`/`ROOT CAUSE`/`FIX` comments.

## ANTI-PATTERNS

- Real credentials in test code; use non-secret placeholders or runtime injection.
- Skipping `yield` cleanup in fixtures.
- Deleting failing tests to "pass".


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `unit/routes/` | directory | `unit/routes/` | high | Flask route and API contract tests |
| `unit/services/` | directory | `unit/services/` | high | application service tests |
| `unit/collector/` | directory | `unit/collector/` | high | isolated collector and ETL tests |
| `frontend/e2e/` | directory | `frontend/e2e/` | med | Playwright browser scenarios and snapshots |
