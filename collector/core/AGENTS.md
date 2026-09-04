# COLLECTOR CORE KNOWLEDGE BASE

## OVERVIEW

Core ETL pipeline modules. Collectors, parsers, database, and authentication.

## FILES

| Path | Role |
| --- | --- |
| `fortigate_collector.py` | FortiGate device collection facade |
| `rate_limiter.py` | Token-bucket + adaptive limiter; `REGTECH_RATE_*` env knobs with WAF-safe defaults |
| `bounded_process.py` | Size/time-bounded subprocess runner backing curl downloads (`run_bounded`, `run_text_bounded`) |
| `control_auth.py` | bearer-token policy for collector control/status/log routes; bypass allowed only in development/testing |
| `validators.py` | IP and CIDR validation |
| `archive_manager.py` | Collection archive retention |
| `data_quality_manager.py` | Collection quality checks |

## SUBPACKAGES

- `regtech/` — REGTECH pipeline: auth + collection orchestration + page fetch + HTML/JSON parsing + normalization + date strategies + error types (mixin composition).
- `multi_source/` — asynchronous multi-source feed aggregation.
- `database/` — persistence, credential decryption, and the collector's DB role boundary (see `database/AGENTS.md`).
- `fortigate/` — FortiGate connection and collection helpers.

## CONVENTIONS

- Parsing separated from collection logic.
- DB `SourceConfig` for per-source rate limiting.
- `ON CONFLICT DO UPDATE` for all upserts.
- Exponential backoff on failures.

## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `FortiGateCollector` | class | `fortigate_collector.py` | high | FortiGate device collection |
| `MultiSourceCollector` | class | `multi_source/collector.py` | high | Async feed aggregation and deduplication |
| `RegtechCollector` | class | `regtech/collector.py` | high | REGTECH ETL pipeline |
| `DatabaseService` | class | `database/service.py` | high | Pooled DB access, credential decryption, batch IP upsert |
| `validate_ip` | function | `validators.py` | med | IP and CIDR validation |
