# COLLECTOR KNOWLEDGE BASE

## OVERVIEW

Independent ETL service on :8545. ZERO imports from `app/` — fully isolated. Coordination via DB/Redis/HTTP only.

## STRUCTURE

```text
collector/
├── run_collector.py         # entry point and lifecycle orchestration
├── config.py                # CollectorConfig: env-based settings + REGTECH credential cache
├── scheduler/                # CollectionScheduler package: manager + operations facade + manual/scheduled/cleanup/stats modules
├── health_server.py         # Flask and Waitress health server on :8545
├── health_routes.py         # health/control route handlers (trigger, force-collection, test-auth)
├── core/                    # ETL pipeline modules
│   ├── regtech/              # REGTECH auth + collection
│   ├── multi_source/         # async feed aggregation
│   ├── fortigate_collector.py  # FortiGate device collection facade
│   └── database/             # collector database service, queries, credential access
├── api/                     # collector API endpoints
└── utils/
```

## HEALTH SERVER ENDPOINTS

- `/health` — open, used by the Docker health check.
- `/status`, `/logs`, `/trigger`, `/api/test-auth/<source>`, `/api/force-collection/<source>` — require a `COLLECTOR_AUTH_TOKEN` bearer token, enforced by `core/control_auth.py`. `DISABLE_JWT_AUTH=true` only bypasses this when `ENVIRONMENT=development` or `TESTING=true`; it has no effect in production. See `docs/decisions/0002-collector-authentication-enforcement.md`.

## SESSION SECURITY

- REGTECH credentials live only in `collector_regtech_credentials`, read through the database layer and decrypted into memory. No environment-variable or file fallback exists; `CollectorConfig.clear_credentials_cache()` scrubs the in-memory cache on every `CollectorApplication.stop()` path, including when the collector was never marked running.

## ANTI-PATTERNS

- Hardcoded URLs (use config/env vars).
- Adding a credential fallback outside `collector_regtech_credentials` (see `core/database/AGENTS.md`).

## NOTES

- `DISABLE_AUTO_COLLECTION=true` starts the scheduler in manual-only mode.
- Adaptive intervals: 300s-3600s based on collection outcomes.
- REGTECH pacing is env-tunable via `REGTECH_RATE_INITIAL/MIN/MAX/BURST` (defaults 0.2/0.1/0.5/1 req/s) and `REGTECH_BLOCK_THRESHOLD` (default 3) — conservative values that avoid the remote WAF's per-IP quota ban; consecutive block signals abort the run with `RegtechCollectionBlockedError`.
- REGTECH page and Excel downloads run through `core/bounded_process.py`, capped at `COLLECTOR_MAX_DOWNLOAD_BYTES` (default 10 MiB). Page curl also passes `--max-filesize`; the bounded reader enforces the limit even for chunked responses.
- REGTECH outbound proxying is controlled by `WARP_PROXY_URL` alone — `collector/core/regtech/collector.py` reads only that variable, and a nonempty value enables the proxy. `WARP_ENABLED` is a compose-level posture flag for documentation/tooling; collector code never reads it. Dev Compose defaults both to a Cloudflare WARP proxy at `host.docker.internal:40000`; the base/release/production overlays set both to disabled/empty.

## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `main` | function | `run_collector.py` | high | Entry point and lifecycle orchestration |
| `CollectionScheduler` | class | `scheduler/manager.py` | high | Scheduled and manual collection control |
| `HealthServer` | class | `health_server.py` | high | Flask and Waitress health server on :8545 |
