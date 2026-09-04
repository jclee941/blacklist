# API ROUTES KNOWLEDGE BASE

## OVERVIEW

JSON REST API surface. Thin handlers — no business logic in routes. Routes are wired into the app two ways: `core/app.py` calls `register_blacklist_routes(app)` directly and registers `auth_bp` as its own blueprint, then registers the single unified `api_bp` (from `routes/api/__init__.py`) which itself absorbs the dashboard, ip_management, monitoring, database, fortinet, analytics, settings, and collection sub-blueprints.

## STRUCTURE

```text
routes/api/
├── __init__.py          # builds the unified api_bp by registering all sub-blueprints below
├── auth_routes.py        # auth_bp: login/logout/me/verify/password (registered separately in app.py)
├── blacklist/            # core blacklist CRUD (5 blueprints, registered via register_blacklist_routes)
├── collection/            # collection ops sub-blueprints, absorbed into api_bp
├── fortinet/              # threat feed + device management, absorbed into api_bp
├── ip_management/         # subpackage: routes/handlers/repository pattern, absorbed into api_bp
├── monitoring/            # Prometheus metrics endpoints, absorbed into api_bp
├── system/                # system status schemas and operations
└── system_api.py, core_api.py, dashboard_api.py, analytics.py, database_api.py, settings_api.py, error_metrics_api.py
```

## CONVENTIONS

- `blacklist/` registers itself via `register_blacklist_routes(app)`; every other API sub-blueprint is registered onto `api_bp` inside `routes/api/__init__.py`.
- All responses: RFC 7807 errors via `APIError` subclasses.
- Services accessed via `current_app.extensions['service_name']`.
- Handlers are dispatchers only — delegate to service layer.
- No runtime DDL/schema-mutation endpoints exist; `database_api.py` exposes read/status operations only.

## ANTI-PATTERNS

- Business logic in route handlers.
- Direct DB queries in routes (use service layer).
- Manual error dict construction (raise typed exception).

## NOTES

- `ip_management/` uses a repository pattern unlike the other route packages; see `ip_management/AGENTS.md`.

## CODE MAP

| Symbol                        | Type     | Location                     | Refs | Role                                            |
| -------------------------------- | -------- | -------------------------------- | ---- | -------------------------------------------------- |
| `register_blacklist_routes`   | function | `blacklist/__init__.py:25`   | high | registers 5 blacklist/whitelist blueprints + error handlers |
| `register_error_handlers`     | function | `blacklist/__init__.py:60`   | med  | global 404/500 JSON handlers                    |
| `api_bp`                      | Blueprint | `api_routes.py`             | high | unified blueprint; absorbs all sub-package blueprints in `__init__.py` |
| `auth_bp`                     | Blueprint | `auth_routes.py:15`         | high | `/api/auth/{login,logout,me,verify,password}`   |
