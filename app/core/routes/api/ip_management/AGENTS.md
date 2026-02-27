# IP MANAGEMENT API KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** d7bb4be
**Branch:** master | **Version:** 3.6.7

## OVERVIEW

Repository-driven API package for whitelist/blacklist management. This package is the only API subtree with explicit `routes` + `handlers` + `repository` layering.

## FILES

| File            | LOC | Role                                                         |
| --------------- | --- | ------------------------------------------------------------ |
| `routes.py`     | 89  | blueprint routes and query/body extraction                   |
| `handlers.py`   | 179 | request orchestration + service/repository dispatch          |
| `repository.py` | 490 | raw SQL access for unified list, whitelist, blacklist, stats |
| `__init__.py`   | 21  | package exports                                              |

## CONVENTIONS

- Use repository methods for SQL access; keep handlers focused on validation/dispatch.
- Preserve parameterized SQL (`%s`) and upsert pattern (`ON CONFLICT DO UPDATE`).
- Normalize datetime fields via repository serializers before returning payloads.

## ANTI-PATTERNS

- Direct SQL in routes/handlers bypassing repository layer.
- Diverging response schema from other API packages without explicit contract updates.
- Building SQL strings from unsanitized user input.

## NOTES

- `repository.py` is a complexity hotspot and should remain covered by dedicated unit tests.
- Unified list queries are built from blacklist/whitelist union logic, not a single static source table.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `IPManagementRepository` | class | `repository.py:14` | high | raw SQL for unified/whitelist/blacklist |
| `ip_management_api_bp` | Blueprint | `routes.py:18` | high | REST routes under /ip-management/ |
| `ip_management_legacy_bp` | Blueprint | `routes.py:20` | med | legacy /ip/ compatibility routes |
| `validate_pagination` | function | `handlers.py:9` | med | page/limit validation |
| `paginated_response` | function | `handlers.py:55` | med | standard paginated JSON builder |