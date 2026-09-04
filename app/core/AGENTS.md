# CORE KNOWLEDGE BASE

## OVERVIEW

Core backend package shared by app factory, routes, services, auth, DB, monitoring, exceptions, and utility helpers.

## STRUCTURE

```text
app/core/
├── app.py              # Flask app factory + middleware wiring (hotspot)
├── app_lifecycle.py    # startup/shutdown lifecycle wiring
├── app_logging.py      # logging setup + in-memory MemoryHandler
├── config.py           # AppConfig env mapping and defaults
├── routes/             # API + legacy web route layers
├── services/           # ServiceFactory-managed DI services
├── auth/               # JWT service, middleware, security, proxy
├── database/           # connection managers and recovery paths
├── monitoring/         # Prometheus metrics definitions
├── exceptions/         # RFC 7807 exception hierarchy
├── utils/               # response/encryption/cache/validation helpers
└── common/, errors/    # legacy shared modules
```

## CODE MAP

| Symbol                   | Type     | Location                                 | Refs | Role                                    |
| ------------------------ | -------- | ------------------------------------------ | ---- | ---------------------------------------- |
| `create_app`             | function | `app.py`                                 | high | factory + middleware + blueprint wiring |
| `AppConfig`              | class    | `config.py`                              | high | env-to-config mapping                   |
| `initialize_services`    | function | `services/service_factory.py`            | high | DI container init, 14 services          |
| `APIError`               | class    | `exceptions/base_exceptions.py`          | high | RFC 7807 error base class               |
| `SmartConnectionManager` | class    | `database/connection_pool_manager.py`    | high | PostgreSQL pooling + backoff            |

## WHERE TO LOOK

| Task                | Location    | Notes                                               |
| ------------------- | ----------- | ----------------------------------------------------- |
| App initialization  | `app.py`    | middleware order, route registration, startup hooks |
| Env/config behavior | `config.py` | URL/DB/Redis/defaults and secret requirements       |
| API/web composition | `routes/`   | API + web package split and blueprint boundaries    |
| DI lifecycle        | `services/` | strict init order via ServiceFactory                |

## ANTI-PATTERNS

- SQLAlchemy/ORM introduction (raw SQL policy only).
- Broad exception swallowing instead of typed `APIError` subclasses.
