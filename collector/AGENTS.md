# COLLECTOR KNOWLEDGE BASE

**Version:** `5.0.0`

## OVERVIEW

Independent ETL service on :8545. ZERO imports from `app/` — fully isolated. Coordination via DB/Redis/HTTP only.

## STRUCTURE

```text
collector/
├── run_collector.py         # entry point and lifecycle orchestration
├── config.py                # CollectorConfig, env-based + credential cache
├── scheduler/               # CollectionScheduler package: manager + operations facade + manual/scheduled/cleanup/stats modules
├── health_server.py         # Flask and Waitress health server on :8545
├── health_routes.py         # health/control route handlers (extracted from health_server)
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
- REGTECH pacing is env-tunable via `REGTECH_RATE_INITIAL/MIN/MAX/BURST` (defaults 0.2/0.1/0.5/1 req/s) and `REGTECH_BLOCK_THRESHOLD` (default 3) — conservative values that avoid the remote WAF's per-IP quota ban; consecutive block signals abort the run with `RegtechCollectionBlockedError`.
- `WARP_PROXY_URL` routes REGTECH outbound through a proxy (e.g., Cloudflare WARP at `host.docker.internal:40000`).
- Adaptive intervals: 300s-3600s based on collection outcomes.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `main` | function | `run_collector.py` | high | Entry point and lifecycle orchestration |
| `CollectionScheduler` | class | `scheduler/manager.py` | high | Scheduled and manual collection control |
| `HealthServer` | class | `health_server.py` | high | Flask and Waitress health server on :8545 |
