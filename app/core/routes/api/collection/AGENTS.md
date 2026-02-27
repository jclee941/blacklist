# COLLECTION API KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** cd16ec1
**Branch:** master | **Version:** 3.6.8

## OVERVIEW

9 files, 18 endpoints for collection management.

## FILES

| File              | Role                                              |
| ----------------- | ------------------------------------------------- |
| `status.py`       | collector health + active-collecting check        |
| `history.py`      | collection history queries + stats                |
| `trigger.py`      | per-source collection trigger                     |
| `sync.py`         | sync with collector + force data refresh          |
| `credentials.py`  | credential CRUD + OTP submission + test           |
| `config.py`       | collection config update                          |
| `sources.py`      | source list + per-source status                   |
| `utils.py`        | `call_collector_api` helper + interval converters |
| `__init__.py`     | 7 blueprint registration                          |

## PAGINATION CONVENTION

- Query params: `page` + `per_page` (default 20), `sort_by` + `sort_order`.
- Response format: `{data: [], total: N, page: N}`.

## NOTES

- Pydantic schemas exist in parent `schemas/` but are NOT wired to these routes.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `register_collection_routes` | function | `__init__.py:18` | high | 7 blueprint registration |
| `collection_credentials_bp` | Blueprint | `credentials.py:24` | high | credential CRUD + OTP + test |
| `collection_status_bp` | Blueprint | `status.py:14` | high | collector health + active check |
| `collection_history_bp` | Blueprint | `history.py:14` | med | history queries + stats |
| `call_collector_api` | function | `utils.py:44` | med | HTTP bridge to collector service |