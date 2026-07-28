# API ROUTES KNOWLEDGE BASE

**Version:** `4.1.0`

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
├── system/             # system status schemas and operations
├── system_api.py       # compatibility export for system routes
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

- `ip_management/` uses a repository pattern unlike the other route packages.
- See `ip_management/AGENTS.md` for package-level repository and handler contracts.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `register_blacklist_routes` | function | `blacklist/__init__.py` | high | Blacklist blueprint registration and error handlers |
| `register_collection_routes` | function | `collection/__init__.py` | high | Collection blueprint registration |
| `register_fortinet_routes` | function | `fortinet/__init__.py` | high | Fortinet blueprint registration and health |
| `register_error_handlers` | function | `blacklist/__init__.py` | med | Legacy 404 and 500 handlers |
