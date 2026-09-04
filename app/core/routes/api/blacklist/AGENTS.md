# BLACKLIST API KNOWLEDGE BASE

## OVERVIEW

Core blacklist API package. 5 blueprints registered via `__init__.py`.

## FILES

| File            | Role                                            |
| --------------- | ----------------------------------------------- |
| `core.py`       | list, stats, check endpoints                    |
| `management.py` | manual add/remove/whitelist                     |
| `batch.py`      | bulk operations                                 |
| `system.py`     | system status                                   |
| `collection.py` | collector bridge (triggers collection from API) |
| `__init__.py`   | 5 blueprint registration + CSRF exemptions      |

## CONVENTIONS

- Registered under `/api`, not a dedicated `/api/blacklist` prefix: `core.py`/`management.py`/`batch.py` mostly use `/blacklist/*` and `/whitelist/*` paths, but `core.py` also exposes `/json`, `system.py` exposes `/system/containers`, `/credential/status`, `/credentials/regtech`, `/database/tables`, and `collection.py` exposes `/collection/regtech/trigger`.
- CSRF exemptions applied at `__init__.py` level.

## KNOWN ISSUES

- Legacy 404/500 handlers in `__init__.py` (should use global handlers).


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `register_blacklist_routes` | function | `__init__.py` | high | 5 blueprint registration + CSRF exemptions |
| `blacklist_core_bp` | Blueprint | `core.py` | high | list/stats/check/export endpoints |
| `blacklist_management_bp` | Blueprint | `management.py` | med | manual add/remove/whitelist |
| `blacklist_batch_bp` | Blueprint | `batch.py` | med | bulk add/remove/update |
| `blacklist_system_bp` | Blueprint | `system.py` | med | system containers/credentials/tables |
