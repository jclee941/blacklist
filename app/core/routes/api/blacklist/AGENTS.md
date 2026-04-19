# BLACKLIST API KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** cd16ec1
**Branch:** master | **Version:** 3.6.9

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

- All endpoints under `/api/blacklist/`.
- CSRF exemptions applied at `__init__.py` level.

## KNOWN ISSUES

- Legacy 404/500 handlers in `__init__.py` (should use global handlers).


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `register_blacklist_routes` | function | `__init__.py:25` | high | 5 blueprint registration + CSRF exemptions |
| `blacklist_core_bp` | Blueprint | `core.py:25` | high | list/stats/check/export endpoints |
| `blacklist_management_bp` | Blueprint | `management.py:18` | med | manual add/remove/whitelist |
| `blacklist_batch_bp` | Blueprint | `batch.py:17` | med | bulk add/remove/update |
| `blacklist_system_bp` | Blueprint | `system.py:15` | med | system containers/credentials/tables |