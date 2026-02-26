# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-26 00:00 Asia/Seoul
**Commit:** 803209d
**Branch:** master | **Version:** 3.6.4

## OVERVIEW

Threat-intelligence platform with three primary runtimes: Flask API (`app/`), independent ETL collector (`collector/`), and Next.js 15 dashboard (`frontend/`). Project policy is strict service isolation + raw SQL only.

## STRUCTURE

```text
./
├── app/                    # Flask API (:2542), manual DI via ServiceFactory
│   └── core/
│       ├── routes/api/     # REST API surface (blacklist, fortinet, collection, ip-mgmt)
│       ├── routes/web/     # legacy Korean admin routes (Jinja2)
│       ├── services/       # 14 services, strict init order
│       ├── auth/           # JWT service + middleware (currently disabled)
│       ├── database/       # connection/recovery infra (not migrations)
│       ├── monitoring/     # Prometheus metrics (counters, histograms, gauges)
│       ├── exceptions/     # typed exception hierarchy (RFC 7807)
│       └── utils/          # response helpers, encryption, caching, validation
├── collector/              # ETL runtime (:8545), independent from app/
│   └── core/
│       ├── regtech/        # REGTECH auth + collection pipeline
│       └── multi_source/   # async feed aggregation pipeline
├── frontend/               # Next.js 15 dashboard (:443)
│   ├── app/                # App Router pages (7 routes)
│   └── lib/                # centralized Axios API client
├── deploy/                 # compose/env/install for offline deployment
├── postgres/               # raw SQL migrations + schema init
│   ├── initdb/             # extension + schema bootstrap
│   └── migrations/         # numbered sequential migrations
└── tests/                  # pytest + mock-fortigate + frontend E2E
```

## CODE MAP

| Symbol                   | Type     | Location                                          | Refs | Role                                                 |
| ------------------------ | -------- | ------------------------------------------------- | ---- | ---------------------------------------------------- |
| `create_app`             | function | `app/core/app.py:51`                              | high | Flask app factory, middleware + blueprint wiring     |
| `initialize_services`    | function | `app/core/services/service_factory.py:37`         | high | ServiceFactory DI container setup, strict init order |
| `BlacklistService`       | class    | `app/core/services/blacklist_service.py:37`       | high | core threat-intel CRUD, sync, system stats           |
| `CollectionService`      | class    | `app/core/services/collection_service.py:31`      | high | collection orchestration across sources              |
| `SmartConnectionManager` | class    | `app/core/database/connection_pool_manager.py:17` | high | PostgreSQL pooling + backoff recovery                |
| `APIError`               | class    | `app/core/exceptions/api_errors.py:62`            | high | RFC 7807 error base class                            |
| `MultiSourceCollector`   | class    | `collector/core/multi_source/collector.py:15`     | high | async feed aggregation + dedup                       |
| `RegtechCollector`       | class    | `collector/core/regtech/collector.py:36`          | high | REGTECH ETL pipeline                                 |
| `collectionApi`          | instance | `frontend/lib/api.ts`                             | high | centralized Axios client for dashboard               |

## WHERE TO LOOK

| Task                              | Location                                      | Notes                                                     |
| --------------------------------- | --------------------------------------------- | --------------------------------------------------------- |
| Flask app init + blueprint wiring | `app/AGENTS.md`                               | app factory, middleware, complexity hotspots              |
| Core backend package boundaries   | `app/core/AGENTS.md`                          | core module topology, cross-cutting contracts             |
| Service lifecycle + DI patterns   | `app/core/services/AGENTS.md`                 | ServiceFactory ordering, extension wiring                 |
| Route layer boundaries            | `app/core/routes/AGENTS.md`                   | API vs web split, naming and ownership traps              |
| Collection service internals      | `app/core/services/collection/AGENTS.md`      | REGTECH auth/data + collection status/history             |
| API route orchestration           | `app/core/routes/api/AGENTS.md`               | route-level patterns, thin handler conventions            |
| Blacklist API package             | `app/core/routes/api/blacklist/AGENTS.md`     | core/management/batch/system/collector bridge             |
| Fortinet API package              | `app/core/routes/api/fortinet/AGENTS.md`      | threat feed + device/log/health endpoints                 |
| Collection API package            | `app/core/routes/api/collection/AGENTS.md`    | 9 files, 18 endpoints, pagination conventions             |
| IP management API package         | `app/core/routes/api/ip_management/AGENTS.md` | repository-based route/handler contract                   |
| Legacy web admin                  | `app/core/routes/web/AGENTS.md`               | Jinja2 Korean UI, CSRF exemptions, credential mgmt        |
| JWT authentication                | `app/core/auth/AGENTS.md`                     | token service, middleware hook, public route list         |
| Database connections              | `app/core/database/AGENTS.md`                 | SmartConnectionManager, recovery, env priority            |
| Prometheus monitoring             | `app/core/monitoring/AGENTS.md`               | metrics, cache metrics, error metrics                     |
| Cross-cutting utilities           | `app/core/utils/AGENTS.md`                    | response format, encryption, caching, validation          |
| Exception hierarchy               | `app/core/exceptions/AGENTS.md`               | RFC 7807 APIError subtypes, raise sites                   |
| Collector runtime                 | `collector/AGENTS.md`                         | scheduler, health server, security lifecycle              |
| Collector ETL core                | `collector/core/AGENTS.md`                    | pipeline architecture, hotspots, conventions              |
| REGTECH package                   | `collector/core/regtech/AGENTS.md`            | auth cache + parser/data processor boundaries             |
| Multi-source package              | `collector/core/multi_source/AGENTS.md`       | async collectors, parser mixins, dedupe merge             |
| Frontend dashboard                | `frontend/AGENTS.md`                          | App Router, API proxy, UI components, test workflow       |
| Frontend pages + routing          | `frontend/app/AGENTS.md`                      | 7 page routes, layout, error boundaries                   |
| Frontend API client               | `frontend/lib/AGENTS.md`                      | centralized Axios client + auth interceptors              |
| Deployment ops                    | `deploy/AGENTS.md`                            | compose inheritance, offline install, release constraints |
| Test conventions                  | `tests/AGENTS.md`                             | markers, mock-fortigate, regression spec format           |
| Database schema                   | `postgres/AGENTS.md`                          | migration strategy, init scripts, table inventory         |

## CONVENTIONS

- Python: Ruff, 120-char line length, 4-space indent; type hints expected.
- TypeScript: Prettier, 100-char line length, 2-space indent, single quotes, semicolons.
- API errors: RFC 7807 style via `APIError` and typed exception hierarchy.
- DI access: Flask services must be retrieved via `current_app.extensions[...]`.
- Frontend API access: route through `frontend/lib/api.ts`; avoid direct `fetch()` in app code.
- SQL: raw only, parameterized `%s`, `ON CONFLICT DO UPDATE`, `IF NOT EXISTS`.
- Korean: operational messages and admin UI use Korean; backend docstrings mixed.

## ANTI-PATTERNS (THIS PROJECT)

- `from app.core.services import X` from route/service code (circular import risk).
- Direct service instantiation in request paths when DI container exists.
- SQLAlchemy/Prisma introduction; project policy is raw SQL.
- Hardcoded environment endpoints when config/env vars already define service URLs.
- Frontend direct DB calls or bypassing HTTP API boundary.
- `from run_app import app` — use `current_app` proxy instead.
- SQL string concatenation — use parameterized `%s` queries.
- Broad `BlacklistError` catch — use specific exception subclass.
- Manual error dict return — raise typed exception, let handler format RFC 7807.

## COMMANDS

```bash
make dev                     # full dev stack (hot reload)
make build                   # production images (requires clean git tree)
make test                    # backend + frontend tests
make test-backend-coverage   # pytest with >=80% threshold
make test-frontend-e2e       # Playwright E2E in frontend/
make release TYPE=patch      # bump, tag, changelog automation
```

## NOTES

- JWT middleware is currently disabled at `app/core/app.py:155` (internal deployment assumption).
- App and collector are intentionally separated processes; zero code sharing, coordination via DB/Redis/HTTP only.
- DI violations in `fortimanager_push_service.py` and `settings_service.py` are intentional (optional db_service param).
- `make build` enforces clean working tree; release pipeline validates `VERSION` against tag.
- 3 rate limiter instances (Flask-Limiter x2 + collector Token Bucket) identified for future consolidation.
- Complexity hotspots: `app.py`(39.91), `blacklist_service.py`(39.43) cognitive complexity scores.
