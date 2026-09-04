# COLLECTION API KNOWLEDGE BASE

## OVERVIEW

10 files for collection management. Registered blueprints mount under `/api/collection` (plus `/api/sync`, `/api/data`, `/api/collection/config` for a couple of routes, see `sync.py`/`config.py`).

## FILES

| File                        | Role                                              |
| --------------------------- | ------------------------------------------------- |
| `status.py`                 | collector health + active-collecting check        |
| `history.py`                | collection history queries + stats                |
| `trigger.py`                | per-source collection trigger                     |
| `sync.py`                   | sync with collector + force data refresh          |
| `credentials.py`            | credential CRUD + OTP submission + test           |
| `credential_validation.py`  | `before_request` payload validation for `credentials.py`'s PUT route |
| `config.py`                 | collection config update                          |
| `sources.py`                | source list + per-source status                   |
| `utils.py`                  | `call_collector_api` helper + interval converters |
| `__init__.py`               | `register_collection_routes()`: registers 7 blueprints + the `credential_validation` hook, applies CSRF exemptions |

## RESPONSE CONTRACT

- `history.py` and most routes return a nested envelope: `{success, data: {...}, timestamp, request_id}`. For `/history`, `data` is `{history: [], total, filtered, page, per_page}`. Pagination uses `page` + `per_page` and, on some list endpoints, `sort_by`/`sort_order`.

## NOTES

- No `schemas/` package exists in this API tree; request bodies are validated inline (see `credential_validation.py`) rather than through a shared schema layer.

## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `register_collection_routes` | function | `__init__.py` | high | registers 7 blueprints + `credential_validation` hook |
| `collection_credentials_bp` | Blueprint | `credentials.py` | high | credential CRUD + OTP + test |
| `collection_status_bp` | Blueprint | `status.py` | high | collector health + active check |
| `collection_history_bp` | Blueprint | `history.py` | med | history queries + stats |
| `call_collector_api` | function | `utils.py` | med | HTTP bridge to collector service |
