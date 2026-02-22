# COLLECTION API KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

1194 lines across 9 files. 18 endpoints for collection management.

## FILES

| File                           | LOC | Endpoints                |
| ------------------------------ | --- | ------------------------ |
| `collection_routes.py`         | 210 | 4 — CRUD operations      |
| `collection_history_routes.py` | 180 | 3 — history queries      |
| `collection_status_routes.py`  | 150 | 3 — collector health     |
| `collection_export_routes.py`  | 130 | 2 — data export          |
| `collection_search_routes.py`  | 120 | 2 — search/filter        |
| `collection_stats_routes.py`   | 110 | 2 — statistics           |
| `collection_bulk_routes.py`    | 100 | 2 — bulk operations      |
| `__init__.py`                  | 94  | — blueprint registration |

## PAGINATION CONVENTION

- Query params: `page` + `per_page` (default 20), `sort_by` + `sort_order`.
- Response format: `{data: [], total: N, page: N}`.

## NOTES

- Pydantic schemas exist in parent `schemas/` but are NOT wired to these routes.
