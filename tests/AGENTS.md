# TESTS KNOWLEDGE BASE

**Generated:** 2026-02-25 15:26 Asia/Seoul
**Commit:** e50fb74
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

Multi-layer testing: pytest (backend) + Vitest (frontend unit) + Playwright (E2E). Coverage target: 80% on `app/core/`.

## STRUCTURE

```text
tests/
├── unit/
│   ├── routes/       # 43 test files
│   ├── services/     # 28 test files
│   ├── collector/    # 24 test files
│   ├── utils/        # 14 test files
│   ├── auth/         # 4 test files
│   ├── monitoring/   # 4 test files
│   ├── common/       # 2 test files
│   ├── errors/       # 1 test file
│   └── smoke/        # 1 smoke test
├── integration/      # 1 integration test
├── e2e/              # 6 Playwright specs + 42 snapshots
└── mock-fortigate/   # standalone Flask mock (320L) + Dockerfile
```

## CONFIG

- `pyproject.toml`: 5 markers (`unit`, `integration`, `security`, `db`, `api`).
- No `conftest.py` — inline fixtures with `yield` cleanup.
- Coverage: `--cov-fail-under=80`.

## CONVENTIONS

- File naming: `test_*.py` (pytest), `*.test.tsx` (Vitest), `*.spec.ts` (Playwright).
- Credentials: `MOCK_CREDENTIALS` from `test_config.py` — never real credentials.
- E2E timeout: 60s. Multi-browser snapshots.
- E2E regression format: `issue-{NUMBER}-{description}.spec.ts` with `PROBLEM`/`ROOT CAUSE`/`FIX` comments.

## MOCK FORTIGATE

- `tests/mock-fortigate/`: standalone Flask app simulating FortiManager JSON-RPC.
- Own `Dockerfile` + `config.py` (27L).

## ANTI-PATTERNS

- Real credentials in test code (use `MOCK_CREDENTIALS`).
- Skipping `yield` cleanup in fixtures.
- Deleting failing tests to "pass".


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `unit/routes/` | directory | `unit/routes/` | high | 43 test files covering all API endpoints |
| `unit/services/` | directory | `unit/services/` | high | 28 test files covering service layer |
| `unit/collector/` | directory | `unit/collector/` | high | 24 test files covering ETL pipelines |
| `mock-fortigate/` | directory | `mock-fortigate/` | med | standalone FortiManager mock (Flask, 320L) |
| `e2e/` | directory | `e2e/` | med | 6 Playwright specs + 42 snapshots |