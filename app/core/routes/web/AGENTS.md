# WEB ROUTES KNOWLEDGE BASE

**Version:** `4.1.0`

## OVERVIEW

Jinja2 legacy Korean admin UI and web-context JSON endpoints.

## FILES

| File | Role |
| --- | --- |
| `api_routes.py` | Web-context JSON endpoints on `web_bp`, not the REST API |
| `blacklist_api_routes.py` | Legacy blacklist list and export endpoints |
| `collection_panel.py` | Collection-panel blueprint |
| `collection_panel_data_routes.py` | Collection-panel data endpoints |
| `collection_panel_runtime_routes.py` | Collection-panel runtime endpoints |
| `collection_panel_view_routes.py` | Collection-panel views |
| `collection_routes.py` | Collection management views and controls |
| `settings.py` | Settings and credential blueprint |
| `admin.py` and `admin_routes.py` | RegTech and database administration |
| `dashboard_routes.py` and `monitoring.py` | Dashboard and monitoring views |
| `__init__.py` | Exposes the parent `web_bp` blueprint |

## CONVENTIONS

- Korean UI throughout.
- Templates in `app/templates/`.

## ANTI-PATTERNS

- Confusing `api_routes.py` with REST API — it serves web-context JSON on `web_bp`, not the API surface.
- Adding non-Korean UI strings without i18n consideration.

## NOTES

- `collection_panel.py` owns the collection-panel blueprint. Its data, runtime, and view handlers are split into companion modules.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `regtech_admin_bp` | Blueprint | `admin.py` | high | RegTech credential administration |
| `collection_bp` | Blueprint | `collection_panel.py` | high | Collection-panel routes |
| `settings_bp` | Blueprint | `settings.py` | high | Settings and credential routes |
| `monitoring_dashboard_bp` | Blueprint | `monitoring.py` | med | Monitoring views |
