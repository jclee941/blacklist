# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-27
**Commit:** d7bb4be
**Branch:** master

## OVERVIEW

Blacklist Intelligence Platform — threat intel for collecting, managing, and analyzing IP blacklist data from **REGTECH** (Korean Financial Security Institute) and **Secudium/ISAP** (SK Shielders). Three-service architecture: Flask API, Python ETL collector, Next.js 15 dashboard. Offline-deployable via Docker bundles.

## STRUCTURE

```text
./
├── app/                        # Flask API service                    :2542
│   ├── run_app.py              # Entry point (Gunicorn WSGI)
│   └── core/                   # Services, routes, auth, database
├── collector/                  # Independent ETL service              :8545
│   ├── run_collector.py        # Entry point (APScheduler)
│   └── core/                   # REGTECH + Secudium + multi-source collectors
├── frontend/                   # Next.js 15 dashboard                 :443
│   ├── app/                    # App Router pages
│   └── lib/                    # API client, hooks, utilities
├── deploy/                     # Docker Compose configs + installer
│   ├── base.yml                # Shared service definitions
│   └── docker-compose.yml      # Dev compose (extends base)
├── postgres/migrations/        # Raw SQL migrations (001-006)
├── tests/                      # pytest backend tests (785+)
├── mock-fortigate/             # Standalone FortiGate API mock
├── docs/                       # Wiki, API reference, architecture
├── .github/workflows/          # CI/CD (ci.yml, release.yml, build-images.yml)
├── Makefile                    # 30+ targets (dev, test, build, deploy)
└── pyproject.toml              # Ruff + mypy config
```

## WHERE TO LOOK

| Task                 | Location                        | Notes                                    |
| -------------------- | ------------------------------- | ---------------------------------------- |
| API endpoints        | `app/core/routes/api/`          | Blueprint-per-domain, JWT-protected      |
| Web admin pages      | `app/core/routes/web/`          | Jinja2 templates, Korean UI              |
| Business logic       | `app/core/services/`            | 14 services via ServiceFactory DI        |
| Auth (JWT + OTP)     | `app/core/auth/`                | Token middleware, OTP email flow         |
| Database queries     | `app/core/database/`            | Raw SQL, connection pooling, no ORM      |
| Collector scheduling | `collector/core/`               | APScheduler triggers, adaptive intervals |
| REGTECH integration  | `collector/core/regtech/`       | Token lifecycle, session management      |
| Multi-source feeds   | `collector/core/multi_source/`  | 14 external threat feed parsers          |
| Frontend pages       | `frontend/app/`                 | Next.js App Router, React Query state    |
| Frontend API client  | `frontend/lib/api.ts`           | Single API gateway, all backend calls    |
| Schema migrations    | `postgres/migrations/`          | Sequential 001-006, raw SQL              |
| Docker deployment    | `deploy/`                       | Compose inheritance, offline installer   |
| Backend tests        | `tests/`                        | pytest, 5 markers, ≥80% coverage target  |
| Frontend tests       | `frontend/__tests__/`           | Vitest 207+ tests                        |
| E2E tests            | `frontend/e2e/`                 | Playwright, Chromium                     |
| CI pipeline          | `.github/workflows/ci.yml`      | Lint → Test → Build → E2E → Push images  |
| Release pipeline     | `.github/workflows/release.yml` | Tag v\* → 5 images → bundle → GHCR       |

## CONVENTIONS

- **Python**: 3.11, Ruff (line-length=120), mypy strict, 4-space indent.
- **TypeScript**: Next.js 15 + React 19, Tailwind v4, Radix UI. 2-space indent.
- **Database**: Raw SQL only. No ORM. Parameterized queries. Sequential migrations.
- **DI**: ServiceFactory pattern in `app/core/services/`. No framework DI.
- **API**: Blueprint-per-domain. JWT auth via `@login_required`. JSON responses.
- **Secrets**: AES-256-GCM encrypted credentials. 1Password `op` CLI for infra secrets.
- **Docker**: All services `network_mode: host`. Named volumes for persistence.
- **Commits**: Conventional Commits (`type(scope): summary`). Squash merge only.
- **CI**: SHA-pinned actions. Reusable workflows from `qws941/.github`.

## COMMANDS

```bash
# Development
make dev                    # Start all 5 Docker services (hot reload)
make down                   # Stop services
make logs                   # View logs

# Testing
make test                   # All tests (backend + frontend)
make test-backend-unit      # pytest only
make test-backend-coverage  # pytest with ≥80% coverage gate
make test-frontend-unit     # Vitest only
make test-e2e               # Playwright E2E

# Verification
make verify-quick           # Ruff lint only (fastest)
make verify                 # lint + types + secrets
make verify-all             # Full CI mirror

# Build & Release
make build                  # Build all Docker images
make bundle                 # Create offline deployment bundle
```

## ANTI-PATTERNS (THIS PROJECT)

- 22 `type: ignore` comments — reduce, never add new ones.
- Hardcoded `0.0.0.0` in some configs — use env vars.
- `time.sleep` in collector scheduler — use APScheduler native waits.
- OTP flow calls wrong endpoint (`submitOtp` → should be `verifyOtp`).
- Never use ORM or SQLAlchemy — raw SQL with parameterized queries only.
- Never import from `app/` in `collector/` — services are fully independent.
- Never skip coverage gate — ≥80% is CI-enforced.

## Review guidelines

- Enforce conventional commit format in PR titles: `type(scope): summary`.
- All GitHub Actions must be SHA-pinned with `# vN` version comment.
- Never approve PRs that add `as any`, `@ts-ignore`, `type: ignore`, or empty `except:` blocks.
- Never approve PRs that hardcode IPs, secrets, or credentials.
- Never approve PRs that add ORM imports (SQLAlchemy, Alembic) — raw SQL only.
- Never approve PRs where `collector/` imports from `app/` — zero coupling.
- PR size ~200 LOC max. Flag PRs exceeding 400 LOC.
- Database changes require a new sequential migration in `postgres/migrations/`.

## NOTES

- Version 3.6.7. Three independent services sharing only PostgreSQL + Redis.
- Collector runs independently — zero imports from `app/`. Separate Docker container.
- Frontend standalone build with embedded SSL certificates for offline deployment.
- `mock-fortigate/` is a standalone Flask app for FortiGate API testing (not production).
- AGENTS.md is synced from `qws941/.github` — local edits get overwritten on next sync push. To persist blacklist-specific content, update sync exclusion in `.github/sync.yml` in the `.github` repo.
