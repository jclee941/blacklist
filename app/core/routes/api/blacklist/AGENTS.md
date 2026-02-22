# BLACKLIST API KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

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
- `system.py` has hardcoded port numbers in mock status — should use config values.
