# COLLECTOR KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

Independent ETL service on :8545. ZERO imports from `app/` — fully isolated. Coordination via DB/Redis/HTTP only.

## STRUCTURE

```text
collector/
├── run_collector.py         # entry point (288L) → CollectorApplication
├── config.py                # CollectorConfig, env-based + credential cache
├── scheduler.py             # APScheduler (700L), daily REGTECH 02:00, IP cleanup midnight
├── scheduler_api.py         # REST trigger for manual collection
├── health_server.py         # Flask+Waitress on :8545 (500L)
├── monitoring_scheduler.py  # periodic health reporting
├── fortimanager_uploader.py # push blacklist to FortiManager
├── core/                    # ETL pipeline modules
│   ├── regtech/             # REGTECH auth + collection
│   ├── multi_source/        # async feed aggregation
│   ├── fortigate_collector.py  # FortiGate device collection (680L)
│   ├── secudium_collector.py   # Secudium platform + OTP auth (676L)
│   └── database.py          # collector DB layer (664L)
├── api/                     # collector API endpoints
└── utils/
    └── otp_email_reader.py  # IMAP OTP reader for Secudium auth
```

## HEALTH SERVER ENDPOINTS

- `/health`, `/status`, `/logs`, `/trigger`
- `/api/test-auth/<source>`, `/config`

## SESSION SECURITY

- Thread-safe token lifecycle: `_token_lock`, 4h TTL, 30min safety margin.
- IP cache eviction: 24h TTL, 100K max, LRU 10%.
- Credential clearing after use.

## ANTI-PATTERNS

- Importing from `app/` (zero code sharing policy).
- `time.sleep()` loops (use scheduler intervals).
- Hardcoded URLs (use config/env vars).
- Missing `aiohttp` for bulk operations.
- Missing locks for shared state.
- Missing TTL+eviction for caches.

## NOTES

- `DISABLE_AUTO_COLLECTION` env var disables scheduled collection.
- Adaptive intervals: 300s-3600s based on collection outcomes.
- Known: `time.sleep` in scheduler (MEDIUM priority fix).
- Known: single-stage Dockerfile (MEDIUM priority optimization).
