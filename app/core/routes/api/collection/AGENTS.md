# AGENTS.md — Collection API Routes

**Generated:** 2026-02-11
**Commit:** 2b9662f | **Version:** 3.5.59
**Parent:** `app/core/routes/api/` | **Total:** 1,194 lines (9 files)

## FILES

| File | Lines | Endpoints | Domain |
|------|-------|-----------|--------|
| `collection_routes.py` | 210 | 4 | CRUD for collection records |
| `collection_history_routes.py` | 180 | 3 | History/audit trail |
| `collection_status_routes.py` | 150 | 3 | Status transitions |
| `collection_export_routes.py` | 130 | 2 | CSV/Excel export |
| `collection_search_routes.py` | 120 | 2 | Search/filter |
| `collection_stats_routes.py` | 110 | 2 | Aggregated statistics |
| `collection_bulk_routes.py` | 100 | 2 | Bulk operations |
| `__init__.py` | 94 | — | Blueprint registration |

## 18 ENDPOINTS TOTAL

All endpoints: JWT-protected (when middleware enabled), DI via `current_app.extensions`, raw SQL queries, RFC 7807 errors.

## SCHEMAS ARE UNUSED

Pydantic schemas exist in `app/core/schemas/` (4 files, 280 LOC) for collection models but are **not imported or used** in any route. All validation is done manually in route handlers.

## PATTERNS

- Every handler starts with `service = current_app.extensions['collection_service']`
- Pagination: `page` + `per_page` query params, default 20
- Sorting: `sort_by` + `sort_order` query params
- All list endpoints return `{data: [], total: int, page: int}`

## ANTI-PATTERNS

| Forbidden | Why |
|-----------|-----|
| Import schema validators | Currently unused by design — manual validation |
| Direct SQL in routes | Use collection_service methods |
| Skip pagination on list endpoints | Frontend expects paginated format |
