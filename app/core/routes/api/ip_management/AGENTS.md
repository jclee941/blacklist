# IP MANAGEMENT API KNOWLEDGE BASE

## OVERVIEW

Repository-driven API package for whitelist/blacklist management. This package is the only API subtree with explicit `routes` + `handlers` + `repository` + `policy` layering.

## FILES

| File            | Role                                                                                                                                                                             |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `routes.py`     | blueprint routes and query/body extraction                                                                                                                                       |
| `handlers.py`   | request orchestration + service/repository dispatch                                                                                                                              |
| `repository.py` | raw SQL access for unified list, whitelist, blacklist, stats                                                                                                                     |
| `policy.py`     | field allowlists (`WHITELIST_CREATE_FIELDS`, `BLACKLIST_CREATE_FIELDS`, etc.), payload dataclasses, and `parse_whitelist_create`/`parse_blacklist_create`/`parse_update_payload` |
| `__init__.py`   | package exports                                                                                                                                                                  |

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

| Symbol                    | Type      | Location        | Refs | Role                                    |
| ------------------------- | --------- | --------------- | ---- | --------------------------------------- |
| `IPManagementRepository`  | class     | `repository.py` | high | raw SQL for unified/whitelist/blacklist |
| `ip_management_api_bp`    | Blueprint | `routes.py`     | high | REST routes under /ip-management/       |
| `ip_management_legacy_bp` | Blueprint | `routes.py`     | med  | legacy /ip/ compatibility routes        |
| `validate_pagination`     | function  | `handlers.py`   | med  | page/limit validation                   |
| `parse_blacklist_create`  | function  | `policy.py`     | med  | validated payload -> `BlacklistCreate`  |
| `parse_whitelist_create`  | function  | `policy.py`     | med  | validated payload -> `WhitelistCreate`  |
