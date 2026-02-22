# COLLECTION SERVICES KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

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
