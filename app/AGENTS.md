# APP KNOWLEDGE BASE

## OVERVIEW

Flask API runtime on :2542. App factory pattern via `create_app()` in `core/app.py`.

## STRUCTURE

```text
app/
├── run_app.py              # entry point, PORT=2542
├── core/
│   ├── app.py              # factory + middleware + blueprint registration
│   ├── app_lifecycle.py    # startup/shutdown wiring (extracted from app.py)
│   ├── app_logging.py      # logging setup + MemoryHandler (extracted from app.py)
│   ├── config.py           # AppConfig environment mapping
│   ├── services/           # application services and ServiceFactory DI
│   ├── routes/api/         # REST JSON (RFC 7807 errors)
│   ├── routes/web/         # Jinja2 legacy Korean admin
│   ├── auth/               # JWT service, middleware, security, proxy
│   ├── database/           # psycopg2 connection managers
│   ├── monitoring/         # Prometheus metrics
│   ├── exceptions/         # typed error hierarchy
│   └── utils/               # response, encryption, cache, validation
├── templates/              # Jinja2 templates (web routes)
└── static/                 # CSS, JS, fonts, images
```

## CODE MAP

| Symbol                | Type     | Location                              | Refs | Role                                    |
| --------------------- | -------- | -------------------------------------- | ---- | ---------------------------------------- |
| `create_app`          | function | `core/app.py:24`                      | high | app factory + middleware + blueprint wiring |
| `initialize_services` | function | `core/services/service_factory.py:36` | high | DI container startup, 14 services       |
| `AppConfig`           | class    | `core/config.py`                      | high | environment-backed config mapping       |

Service-level symbols in `core/services/AGENTS.md`. Auth symbols in `core/auth/AGENTS.md`.

## WHERE TO LOOK

| Task                     | Location                           | Notes                                                 |
| ------------------------ | ----------------------------------- | ----------------------------------------------------- |
| App factory + middleware | `core/app.py`                      | csrf, JWT hook, request_id, security headers, compression |
| Blueprint registration   | `core/app.py`                      | mix of `register_blacklist_routes(app)`, direct `app.register_blueprint(auth_bp/api_bp/proxy_bp)` |
| Core package topology    | `core/AGENTS.md`                   | boundaries across routes/services/auth/db/utils       |
| Config properties        | `core/config.py`                   | DB, Redis, URLs, secrets, admin, JWT, collection      |
| DI container             | `core/services/service_factory.py` | strict init order, `current_app.extensions[...]`      |

## MAINTENANCE HOTSPOTS

| File                                         | Concern                        |
| -------------------------------------------- | ------------------------------ |
| `core/app.py`                                | app factory, middleware, blueprint wiring |
| `core/services/secure_credential_service.py` | AES-256-GCM credential storage |
| `core/services/auth_state_service.py`        | transactional admin password/session state |
| `core/services/blacklist_service.py`         | blacklist query and mutation   |

## ANTI-PATTERNS

- Direct service instantiation — use `current_app.extensions['service_name']`.
- Business logic in route handlers — routes are thin dispatchers only.
- `from run_app import app` — use `current_app` proxy.

## NOTES

- Global JWT enforcement is active by default (`app.before_request(jwt_required_hook)`); public routes use `@public` or the static/favicon/robots path prefixes.
- `before_request` order: `csrf_protect_web_only` → `jwt_required_hook` → `generate_request_id`.
- `DISABLE_JWT_AUTH=true` is rejected outside `development`/testing at factory startup.
