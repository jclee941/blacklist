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

## WHERE TO LOOK

| Task                     | Location                           | Notes                                                                                             |
| ------------------------ | ---------------------------------- | ------------------------------------------------------------------------------------------------- |
| App factory + middleware | `core/app.py`                      | csrf, JWT hook, request_id, security headers, compression                                         |
| Blueprint registration   | `core/app.py`                      | mix of `register_blacklist_routes(app)`, direct `app.register_blueprint(auth_bp/api_bp/proxy_bp)` |
| Core package topology    | `core/AGENTS.md`                   | boundaries across routes/services/auth/db/utils                                                   |
| Config properties        | `core/config.py`                   | DB, Redis, URLs, secrets, admin, JWT, collection                                                  |
| DI container             | `core/services/service_factory.py` | strict init order, `current_app.extensions[...]`                                                  |

## MAINTENANCE HOTSPOTS

| File                                         | Concern                                              |
| -------------------------------------------- | ---------------------------------------------------- |
| `core/app.py`                                | app factory, middleware, blueprint wiring            |
| `core/services/secure_credential_service.py` | Fernet-based credential storage (PBKDF2-derived key) |
| `core/services/auth_state_service.py`        | transactional admin password/session state           |
| `core/services/blacklist_service.py`         | blacklist query and mutation                         |

## NOTES

- Global JWT enforcement is active by default (`app.before_request(jwt_required_hook)`); public routes use `@public` or the static/favicon/robots path prefixes.
- `before_request` order: `csrf_protect_web_only` → `jwt_required_hook` → `generate_request_id`.
- `DISABLE_JWT_AUTH=true` is rejected outside `development`/testing at factory startup.
- Detailed core conventions, service symbols, and route rules live under `core/AGENTS.md`.
