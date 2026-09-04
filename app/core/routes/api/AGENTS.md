# API ROUTES KNOWLEDGE BASE

## OVERVIEW

JSON REST API composition layer. `core/app.py` calls `register_blacklist_routes(app)`, registers `auth_bp`, then registers unified `api_bp`; `routes/api/__init__.py` absorbs the dashboard, primary IP-management, monitoring, database, Fortinet, analytics, settings, and collection sub-blueprints. `ip_management_legacy_bp` is imported but not registered.

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

## LOCAL RULES

- `blacklist/` registers itself via `register_blacklist_routes(app)`; unified sub-blueprints are registered onto `api_bp` inside `routes/api/__init__.py`, except the imported-but-unregistered `ip_management_legacy_bp`.
- No runtime DDL/schema-mutation endpoints exist; `database_api.py` exposes read/status operations only.

## NOTES

- `ip_management/` uses a repository pattern unlike the other route packages; see `ip_management/AGENTS.md`.

## CODE MAP

| Symbol                      | Type      | Location                | Refs | Role                                                                  |
| --------------------------- | --------- | ----------------------- | ---- | --------------------------------------------------------------------- |
| `register_blacklist_routes` | function  | `blacklist/__init__.py` | high | registers 5 blacklist/whitelist blueprints + error handlers           |
| `register_error_handlers`   | function  | `blacklist/__init__.py` | med  | global 404/500 JSON handlers                                          |
| `api_bp`                    | Blueprint | `../api_routes.py`      | high | created one level up; `routes/api/__init__.py` absorbs sub-blueprints |
| `auth_bp`                   | Blueprint | `auth_routes.py`        | high | `/api/auth/{login,logout,me,verify,password}`                         |
