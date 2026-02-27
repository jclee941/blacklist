# COLLECTOR CORE KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** d7bb4be
**Branch:** master | **Version:** 3.6.7

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

- Recent updates include token lifecycle hardening and major type-check cleanup.
- Hotspots: `fortigate_collector.py` and `secudium_collector.py` (~680L each).


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `FortiGateCollector` | class | `fortigate_collector.py` | high | FortiGate device collection (680L hotspot) |
| `SecudiumCollector` | class | `secudium_collector.py` | high | Secudium platform + OTP auth (676L hotspot) |
| `MultiSourceCollector` | class | `multi_source/collector.py:15` | high | async feed aggregation + dedup |
| `RegtechCollector` | class | `regtech/collector.py:36` | high | REGTECH ETL pipeline |
| `validate_ip` | function | `validators.py:17` | med | IP/CIDR validation + normalization |