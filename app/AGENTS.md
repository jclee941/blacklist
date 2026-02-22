# APP KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

Flask API runtime on :2542. App factory pattern via `create_app()` in `core/app.py`.

## STRUCTURE

```text
app/
├── run_app.py              # entry point, PORT=2542
├── core/
│   ├── app.py              # factory + middleware (479L, complexity 39.91)
│   ├── config.py           # AppConfig: 48 @property → os.getenv()
│   ├── services/           # 14 services, ServiceFactory DI
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

## WHERE TO LOOK

| Task                     | Location                           | Notes                                                 |
| ------------------------ | ---------------------------------- | ----------------------------------------------------- |
| App factory + middleware | `core/app.py`                      | csrf, request_id, security headers, compression       |
| Blueprint registration   | `core/app.py`                      | modular `register_*_routes(app)` functions            |
| Config properties        | `core/config.py`                   | DB, Redis, URLs, Secrets, FMG, Admin, JWT, Collection |
| DI container             | `core/services/service_factory.py` | strict init order, `current_app.extensions[...]`      |

## COMPLEXITY HOTSPOTS

| File                                         | LOC | Concern                         |
| -------------------------------------------- | --- | ------------------------------- |
| `core/app.py`                                | 479 | cognitive complexity 39.91      |
| `core/routes/api/system_api.py`              | 648 | system status endpoints         |
| `core/services/secure_credential_service.py` | 624 | AES-256-GCM credential storage  |
| `core/routes/web/admin.py`                   | 620 | RegTech credential management   |
| `core/routes/web/collection_panel.py`        | 603 | collection UI + CSRF-exempt API |
| `core/services/collection_service.py`        | 596 | collection orchestration        |
| `core/services/blacklist_service.py`         | 534 | complexity 39.43                |

## ANTI-PATTERNS

- Direct service instantiation — use `current_app.extensions['service_name']`.
- Business logic in route handlers — routes are thin dispatchers only.
- `from run_app import app` — use `current_app` proxy.

## NOTES

- JWT middleware DISABLED at `core/app.py:154-156` (internal deployment).
- DI violations in `fortimanager_push_service.py` and `settings_service.py` are intentional (optional `db_service` param).
- 3 rate limiter instances (Flask-Limiter ×2) identified for future consolidation.
- Middleware chain: `csrf_protect_web_only` → `generate_request_id` → `add_security_headers` → `compress_response`.
