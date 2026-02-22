# API ROUTES KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

JSON REST API surface. Thin handlers — no business logic in routes.

## STRUCTURE

```text
routes/api/
├── blacklist/          # core blacklist CRUD (5 blueprints)
├── collection/         # collection ops (9 files, 18 endpoints)
├── fortinet/           # threat feed + device management
├── ip_management/      # subpackage: routes/handlers/repository pattern
├── monitoring/         # Prometheus metrics endpoints
├── schemas/            # Pydantic schemas (4 files, 280 LOC) — UNUSED
├── system_api.py       # 648L, system status endpoints
├── dashboard_api.py    # dashboard data aggregation
├── analytics.py        # analytics endpoints
├── database_api.py     # DB admin endpoints
└── migration.py        # migration utilities
```

## CONVENTIONS

- Blueprint registration via modular `register_*_routes(app)` functions.
- All responses: RFC 7807 errors via `APIError` subclasses.
- Services accessed via `current_app.extensions['service_name']`.
- Handlers are dispatchers only — delegate to service layer.

## ANTI-PATTERNS

- Business logic in route handlers.
- Direct DB queries in routes (use service layer).
- Manual error dict construction (raise typed exception).

## NOTES

- `schemas/` directory exists but Pydantic schemas are NOT wired to validation.
- `system_api.py` (648L) is the largest single route file.
- `ip_management/` uses repository pattern (unlike other route packages).
