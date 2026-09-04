# COLLECTION SERVICES KNOWLEDGE BASE

## OVERVIEW

Collection-domain service package. Manages REGTECH auth/data scraping, collection history, status tracking, and validation.

## FILES

| File                         | Role                                                                                                                    |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `regtech_data.py`            | thin facade: re-exports discovery/processing functions, hosts `REGTECHDataCollector`                                    |
| `regtech_data_discovery.py`  | REGTECH portal URL discovery + live data collection orchestration                                                       |
| `regtech_data_processing.py` | HTML parsing, link extraction, confidence/date extraction, normalization                                                |
| `regtech_auth.py`            | session authentication + cache                                                                                          |
| `collection_history.py`      | history persistence + statistics                                                                                        |
| `collection_persistence.py`  | `save_collection_data` upsert helper for `blacklist_ips`                                                                |
| `collection_status.py`       | collector health monitoring                                                                                             |
| `collection_validator.py`    | input validation + normalization                                                                                        |
| `threat_intelligence.py`     | TI integration stubs                                                                                                    |
| `__init__.py`                | package exports (`regtech_collector`, `validator`, `history_manager`, `status_manager`, `regtech_auth`, `threat_intel`) |

## CONVENTIONS

- Korean operational messages expected throughout.
- Auth cache uses timestamp-based TTL validation.
- Data processing pipeline: scrape → parse → validate → normalize → persist.

## NOTES

- `regtech_data.py` re-exports from `regtech_data_discovery.py` and `regtech_data_processing.py` via `importlib`; edit the discovery/processing modules directly rather than `regtech_data.py`.
- Separate from `collector/core/regtech/`, which is the collector-side ETL pipeline; this package is the app-side service layer.

## CODE MAP

| Symbol                      | Type     | Location                     | Refs | Role                                                      |
| --------------------------- | -------- | ---------------------------- | ---- | --------------------------------------------------------- |
| `REGTECHDataCollector`      | class    | `regtech_data.py`            | high | thin wrapper delegating to discovery/processing modules   |
| `collect_real_regtech_data` | function | `regtech_data_discovery.py`  | high | live REGTECH portal collection with dynamic URL discovery |
| `parse_regtech_data`        | function | `regtech_data_processing.py` | high | HTML parsing into blacklist entries                       |
| `REGTECHAuthManager`        | class    | `regtech_auth.py`            | high | session auth + cache TTL validation                       |
| `CollectionHistoryManager`  | class    | `collection_history.py`      | med  | persistence + statistics                                  |
| `save_collection_data`      | function | `collection_persistence.py`  | med  | upsert into `blacklist_ips`                               |
| `CollectionStatusManager`   | class    | `collection_status.py`       | med  | collector health monitoring                               |
| `CollectionValidator`       | class    | `collection_validator.py`    | med  | input validation + normalization                          |
