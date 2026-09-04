# ROUTES KNOWLEDGE BASE

## OVERVIEW

Route layer split between REST API packages and legacy web/Jinja2 packages. Keep orchestration thin and push logic into services/repositories.

## STRUCTURE

```text
app/core/routes/
├── api/                 # REST JSON surface (blacklist/fortinet/collection/ip-management/monitoring/system)
└── web/                 # legacy Korean admin views + web-context JSON endpoints
```

## WHERE TO LOOK

| Task                            | Location                                             | Notes                                               |
| ------------------------------- | ---------------------------------------------------- | --------------------------------------------------- |
| API route contracts             | `api/AGENTS.md`                                      | unified `api_bp` composition and thin-handler rules |
| Legacy admin behavior           | `web/AGENTS.md`                                      | CSRF exemptions, template coupling, Korean UI       |
| IP management subpackage        | `api/ip_management/AGENTS.md`                        | repository + handler split unique to API layer      |
| Collection/Fortinet subpackages | `api/collection/AGENTS.md`, `api/fortinet/AGENTS.md` | per-package blueprint detail                        |

## CONVENTIONS

- API responses follow RFC 7807 exception formatting through shared error handlers.
- Route modules fetch dependencies from `current_app.extensions` instead of direct construction.
- Keep route files as dispatchers; business/data logic belongs in service or repository modules.

## ANTI-PATTERNS

- Mixing web-context endpoints with REST API namespaces.
- Direct SQL in routes when repository/service abstractions already exist.
- Returning ad hoc error dicts instead of raising typed exceptions.

## CODE MAP

| Symbol                        | Type     | Location              | Refs | Role                          |
| ----------------------------- | -------- | --------------------- | ---- | ----------------------------- |
| `register_websocket_handlers` | function | `websocket_routes.py` | med  | SocketIO event handler wiring |

Route-specific CODE MAPs in `api/AGENTS.md` and `web/AGENTS.md`.
