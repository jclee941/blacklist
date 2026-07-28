# APP KNOWLEDGE BASE

## OVERVIEW

Flask API runtime on :2542. App factory pattern via `create_app()` in `core/app.py`.

## STRUCTURE

```text
app/
├── run_app.py              # entry point, PORT=2542
├── core/
│   ├── app.py              # factory + middleware
│   ├── config.py           # AppConfig environment mapping
│   ├── services/           # application services and ServiceFactory DI
│   ├── routes/api/         # REST JSON (RFC 7807 errors)
│   ├── routes/web/         # Jinja2 legacy Korean admin
│   ├── auth/               # JWT (DISABLED at app.py:155)
│   ├── database/           # psycopg2 connection managers
│   ├── monitoring/         # Prometheus metrics
│   ├── exceptions/         # typed error hierarchy
│   └── utils/              # response, encryption, cache, validation
├── templates/              # Jinja2 templates (web routes)
└── static/                 # CSS, JS, fonts, images
```

## CODE MAP

| Symbol                | Type     | Location                              | Refs | Role                                    |
| --------------------- | -------- | ------------------------------------- | ---- | --------------------------------------- |
| `create_app`          | function | `core/app.py:51`                      | high | app factory + middleware chain          |
| `initialize_services` | function | `core/services/service_factory.py:37` | high | DI container startup, strict init order |
| `AppConfig`           | class    | `core/config.py`                      | high | environment-backed config mapping       |

Service-level symbols in `core/services/AGENTS.md`.

## WHERE TO LOOK

| Task                     | Location                           | Notes                                                 |
| ------------------------ | ---------------------------------- | ----------------------------------------------------- |
| App factory + middleware | `core/app.py`                      | csrf, request_id, security headers, compression       |
| Blueprint registration   | `core/app.py`                      | modular `register_*_routes(app)` functions            |
| Core package topology    | `core/AGENTS.md`                   | boundaries across routes/services/auth/db/utils       |
| Config properties        | `core/config.py`                   | DB, Redis, URLs, Secrets, Admin, JWT, Collection |
| DI container             | `core/services/service_factory.py` | strict init order, `current_app.extensions[...]`      |

## MAINTENANCE HOTSPOTS

| File                                         | Concern                        |
| -------------------------------------------- | ------------------------------ |
| `core/app.py`                                | app factory and middleware     |
| `core/services/secure_credential_service.py` | encrypted credential storage   |
| `core/services/collection_service.py`        | collection orchestration       |
| `core/services/blacklist_service.py`         | blacklist query and mutation   |

## ANTI-PATTERNS

- Direct service instantiation — use `current_app.extensions['service_name']`.
- Business logic in route handlers — routes are thin dispatchers only.
- `from run_app import app` — use `current_app` proxy.

## NOTES

- Global JWT enforcement is disabled; token endpoints remain available.
- Middleware chain: `csrf_protect_web_only` → `generate_request_id` → `add_security_headers` → `compress_response`.
