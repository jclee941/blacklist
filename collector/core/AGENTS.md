# COLLECTOR CORE KNOWLEDGE BASE

**Version:** `4.1.0`

## OVERVIEW

Core ETL pipeline modules. Collectors, parsers, database, and authentication.

## FILES

| Path | Role |
| --- | --- |
| `fortigate_collector.py` | FortiGate device collection facade |
| `database/` | Collector database service, queries, and credential access |
| `fortigate/` | FortiGate SSH collection helpers |
| `validators.py` | IP and CIDR validation |
| `archive_manager.py` | Collection archive retention |
| `data_quality_manager.py` | Collection quality checks |

## SUBPACKAGES

- `regtech/` — REGTECH authentication and collection pipeline.
- `multi_source/` — asynchronous multi-source feed aggregation.
- `database/` — persistence and credential boundaries.
- `fortigate/` — FortiGate connection and collection helpers.

## CONVENTIONS

- Parsing separated from collection logic.
- DB `SourceConfig` for per-source rate limiting.
- `ON CONFLICT DO UPDATE` for all upserts.
- Exponential backoff on failures.

## NOTES

- Recent updates include token lifecycle hardening and major type-check cleanup.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `FortiGateCollector` | class | `fortigate_collector.py` | high | FortiGate device collection |
| `MultiSourceCollector` | class | `multi_source/collector.py` | high | Async feed aggregation and deduplication |
| `RegtechCollector` | class | `regtech/collector.py` | high | REGTECH ETL pipeline |
| `validate_ip` | function | `validators.py` | med | IP and CIDR validation |
