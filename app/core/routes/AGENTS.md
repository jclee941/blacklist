# ROUTES KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** cd16ec1
**Branch:** master | **Version:** 3.6.9

## OVERVIEW

Route layer split between REST API packages and legacy web/Jinja2 packages. Keep orchestration thin and push logic into services/repositories.

## STRUCTURE

```text
app/core/routes/
├── api/                 # REST JSON surface (blacklist/fortinet/collection/ip-management)
└── web/                 # legacy Korean admin views + web-context JSON endpoints
```

## WHERE TO LOOK

| Task                     | Location                      | Notes                                          |
| ------------------------ | ----------------------------- | ---------------------------------------------- |
| API route contracts      | `api/AGENTS.md`               | blueprint registration and thin-handler rules  |
| Legacy admin behavior    | `web/AGENTS.md`               | CSRF exemptions, template coupling, Korean UI  |
| IP management subpackage | `api/ip_management/AGENTS.md` | repository + handler split unique to API layer |

## CONVENTIONS

- API responses follow RFC 7807 exception formatting through shared error handlers.
- Route modules fetch dependencies from `current_app.extensions` instead of direct construction.
- Keep route files as dispatchers; business/data logic belongs in service or repository modules.

## ANTI-PATTERNS

- Mixing web-context endpoints with REST API namespaces.
- Direct SQL in routes when repository/service abstractions already exist.
- Returning ad hoc error dicts instead of raising typed exceptions.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `register_websocket_handlers` | function | `websocket_routes.py:16` | med | SocketIO event handler wiring |

Route-specific CODE MAPs in `api/AGENTS.md` and `web/AGENTS.md`.