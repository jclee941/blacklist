# WEB ROUTES KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** d7bb4be
**Branch:** master | **Version:** 3.6.7

## OVERVIEW

Jinja2 legacy Korean admin UI. 3139 lines across 10 files.

## FILES

| File                    | LOC | Role                                            |
| ----------------------- | --- | ----------------------------------------------- |
| `admin.py`              | 619 | RegTech credential management (hotspot)         |
| `api_routes.py`         | 569 | web-context JSON API on `web_bp` (NOT REST API) |
| `collection_panel.py`   | 606 | collection UI + CSRF-exempt API (hotspot)       |
| `settings.py`           | 440 | system settings UI                              |
| `admin_routes.py`       | 269 | system/user admin                               |
| `collection_routes.py`  | 237 | collection management UI                        |
| `dashboard_routes.py`   | 187 | dashboard views                                 |
| `credentials_routes.py` | 113 | credential management                           |
| `monitoring.py`         | 86  | monitoring views                                |
| `__init__.py`           | 13  | blueprint registration                          |

## CONVENTIONS

- Korean UI throughout.
- CSRF exemptions applied to `collection_panel.py` API endpoints.
- Templates in `app/templates/`.

## ANTI-PATTERNS

- Confusing `api_routes.py` with REST API — it serves web-context JSON on `web_bp`, not the API surface.
- Adding non-Korean UI strings without i18n consideration.

## NOTES

- Complexity hotspots: `admin.py`, `collection_panel.py`, `api_routes.py`.
- `api_routes.py` naming is confusing — consider renaming to `web_api_routes.py`.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `regtech_admin_bp` | Blueprint | `admin.py:16` | high | RegTech credential management (9 endpoints) |
| `collection_bp` | Blueprint | `collection_panel.py:14` | high | collection UI + CSRF-exempt API (12 endpoints) |
| `settings_bp` | Blueprint | `settings.py:17` | high | system settings CRUD (11 endpoints) |
| `credentials_bp` | Blueprint | `credentials_routes.py:8` | med | credential management |
| `monitoring_dashboard_bp` | Blueprint | `monitoring.py:13` | med | monitoring views |