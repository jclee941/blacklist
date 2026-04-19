# COLLECTION SERVICES KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** cd16ec1
**Branch:** master | **Version:** 3.6.9

## OVERVIEW

Collection-domain service package. Manages REGTECH auth/data scraping, collection history, status tracking, and validation.

## FILES

| File                      | LOC  | Role                                         |
| ------------------------- | ---- | -------------------------------------------- |
| `regtech_data.py`         | >600 | scraping, parsing, data extraction (hotspot) |
| `regtech_auth.py`         | ~150 | session authentication + cache               |
| `collection_history.py`   | ~200 | persistence + statistics                     |
| `collection_status.py`    | ~120 | collector health monitoring                  |
| `collection_validator.py` | ~100 | input validation + normalization             |
| `threat_intelligence.py`  | ~80  | TI integration stubs                         |

## CONVENTIONS

- Korean operational messages expected throughout.
- Auth cache uses timestamp-based TTL validation.
- Data processing pipeline: scrape → parse → validate → normalize → persist.

## NOTES

- `regtech_data.py` is the primary complexity hotspot (>600 LOC).
- Separate from `collector/core/regtech/` — this is the app-side service layer.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `REGTECHDataCollector` | class | `regtech_data.py:13` | high | scraping + parsing + extraction (>600L hotspot) |
| `REGTECHAuthManager` | class | `regtech_auth.py:12` | high | session auth + cache TTL validation |
| `CollectionHistoryManager` | class | `collection_history.py:14` | med | persistence + statistics |
| `CollectionStatusManager` | class | `collection_status.py:14` | med | collector health monitoring |
| `CollectionValidator` | class | `collection_validator.py:14` | med | input validation + normalization |