# COLLECTOR KNOWLEDGE BASE

**Version:** `4.1.0`

## OVERVIEW

Independent ETL service on :8545. ZERO imports from `app/` — fully isolated. Coordination via DB/Redis/HTTP only.

## STRUCTURE

```text
collector/
├── run_collector.py         # entry point and lifecycle orchestration
├── config.py                # CollectorConfig, env-based + credential cache
├── scheduler/               # CollectionScheduler and collection operations
├── health_server.py         # Flask and Waitress health server on :8545
├── core/                    # ETL pipeline modules
│   ├── regtech/             # REGTECH auth + collection
│   ├── multi_source/        # async feed aggregation
│   ├── fortigate_collector.py  # FortiGate device collection (680L)
│   └── database/            # collector database service and queries
├── api/                     # collector API endpoints
└── utils/
```

## HEALTH SERVER ENDPOINTS

- `/health`, `/status`, `/logs`, `/trigger`
- `/api/test-auth/<source>`, `/api/force-collection/<source>`

## SESSION SECURITY

- Credentials are read from the collector database layer and can be cleared from the in-memory cache on shutdown.

## ANTI-PATTERNS

- Importing from `app/` (zero code sharing policy).
- Hardcoded URLs (use config/env vars).

## NOTES

- `DISABLE_AUTO_COLLECTION=true` starts the scheduler in manual-only mode.
- Adaptive intervals: 300s-3600s based on collection outcomes.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `main` | function | `run_collector.py` | high | Entry point and lifecycle orchestration |
| `CollectionScheduler` | class | `scheduler/manager.py` | high | Scheduled and manual collection control |
| `HealthServer` | class | `health_server.py` | high | Flask and Waitress health server on :8545 |
