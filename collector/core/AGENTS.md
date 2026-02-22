# COLLECTOR CORE KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

Core ETL pipeline modules. Collectors, parsers, database, and authentication.

## FILES

| File                     | LOC  | Role                                   |
| ------------------------ | ---- | -------------------------------------- |
| `fortigate_collector.py` | 680  | FortiGate device collection (hotspot)  |
| `secudium_collector.py`  | 676  | Secudium platform + OTP auth (hotspot) |
| `database.py`            | 664  | maxconn=20, IP cache eviction          |
| `authentication.py`      | ~100 | Fernet credential decryption           |
| `data_normalizer.py`     | ~80  | IP/domain normalization                |

## SUBPACKAGES

- `regtech/` — REGTECH auth + collection pipeline (3 files).
- `multi_source/` — async multi-source feed aggregation (3 files).

## CONVENTIONS

- Parsing separated from collection logic.
- DB `SourceConfig` for per-source rate limiting.
- `ON CONFLICT DO UPDATE` for all upserts.
- Exponential backoff on failures.

## NOTES

- v3.5.64: token lifecycle hardening.
- v3.5.60: resolved 91 mypy errors.
- Hotspots: `fortigate_collector.py` and `secudium_collector.py` (~680L each).
