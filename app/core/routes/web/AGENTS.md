# AGENTS.md — Web Routes (Server-Rendered + Legacy API)

**Generated:** 2026-02-12
**Commit:** 83e7d28 | **Version:** 3.5.60
**Parent:** `app/core/routes/` | **Total:** 3,139 lines

## OVERVIEW

Jinja2-rendered admin panels and legacy web API endpoints. Korean UI strings throughout. Distinct from `api/` which is JSON-only.

## STRUCTURE

| File | Lines | Purpose |
|------|-------|---------|
| `admin.py` | 619 | RegTech credential management panel |
| `admin_routes.py` | 269 | General admin operations (system, users) |
| `api_routes.py` | 569 | Web-facing API (search, stats) — returns JSON but mounted on `web_bp` |
| `collection_panel.py` | 606 | Collection management UI + CSRF-exempt API endpoints |
| `collection_routes.py` | 237 | Collection trigger/status endpoints |
| `credentials_routes.py` | 113 | Encrypted credential CRUD |
| `dashboard_routes.py` | 187 | Main dashboard rendering |
| `monitoring.py` | 86 | Health/metrics UI |
| `settings.py` | 440 | System settings panel |
| `__init__.py` | 13 | Imports `web_bp`, registers `api_routes` |

## WHERE TO LOOK

| Task | File | Notes |
|------|------|-------|
| Add admin panel page | `admin.py` or `admin_routes.py` | Template in `templates/` |
| Add web-facing API | `api_routes.py` | JSON response, still on `web_bp` |
| Collection UI changes | `collection_panel.py` | Blueprint: `simple_collection` at `/collection-panel` |
| Credential management | `credentials_routes.py` | Uses `secure_credential_service` |
| Dashboard widgets | `dashboard_routes.py` | Renders `dashboard.html` |
| System settings | `settings.py` | 440L — settings CRUD |

## CONVENTIONS

- **Blueprint pattern**: Each major feature gets its own Blueprint (e.g., `regtech_admin`, `simple_collection`)
- **Korean UI**: All user-facing strings in Korean (comments too)
- **CSRF**: Collection panel uses `@csrf.exempt` for its API-like endpoints
- **Dual field support**: `admin.py` accepts both `username/password` AND `regtech_id/regtech_pw` field names

## ANTI-PATTERNS

| Forbidden | Why |
|-----------|-----|
| Business logic in route handlers | Belongs in services layer |
| HTML responses in `/api/` routes | `/api/` = JSON only; this dir's `api_routes.py` is the exception (legacy) |

## COMPLEXITY HOTSPOTS

- `admin.py` (619L) — Dual credential format support, validation logic
- `collection_panel.py` (606L) — Mixed template rendering + API endpoints
- `api_routes.py` (569L) — Legacy search with complex SQL joins

## NOTES

- `api_routes.py` is confusingly named — it's web API routes (on `web_bp`), NOT the REST API (that's in `routes/api/`)
- `__init__.py` wires `api_routes` into the parent `web_bp` via import side-effect
