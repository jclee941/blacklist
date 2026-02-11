# COLLECTOR KNOWLEDGE BASE

**Generated:** 2026-02-11
**Commit:** f082182 | **Version:** 3.5.57
**Role:** ETL Service (Data Collection)
**Parent:** [../AGENTS.md](../AGENTS.md)

## OVERVIEW

Independent ETL service. Collects blacklists from external sources, normalizes, stores to DB.
Fully separated from `app/` — own DB pool, own process. Port 8545.

## STRUCTURE

```
run_collector.py        # Entry point (:8545)
config.py               # Environment config
scheduler.py            # APScheduler-based scheduling
scheduler_api.py        # Collection trigger REST API
health_server.py        # K8s liveness/readiness
monitoring_scheduler.py # Monitoring schedule
core/                   # Collection logic (→ core/AGENTS.md)
  regtech/              # Regtech collection package
  multi_source/         # Multi-source collection package
```

## HOW TO: Add Collection Source

1. Create collector class in `core/` (inject `CollectorDatabase`)
2. Register schedule in `scheduler.py`
3. (Optional) Add `/api/force-collection/SOURCE` trigger in `scheduler_api.py`

## ANTI-PATTERNS

| Forbidden | Alternative | Reason |
|-----------|-------------|--------|
| `from app.* import` | Independent implementation | Service boundary violation |
| `time.sleep()` loops | APScheduler | Main thread blocking |
| Infinite retry | Backoff + max count | Resource exhaustion |
| Sync bulk HTTP | `aiohttp` / ThreadPool | Performance |
| Hardcoded URLs | Environment variables | Docker compatibility |

## KNOWN ISSUES

| Issue | Location | Severity |
|-------|----------|----------|
| Hardcoded app URL | `fortimanager_uploader.py:36,77` | CRITICAL |
| `time.sleep()` blocking | `scheduler.py` | MEDIUM |
| Single-stage Dockerfile | `Dockerfile` — Playwright bloat | MEDIUM |


## COMMUNICATION

```bash
# Trigger collection
curl -X POST http://blacklist-collector:8545/api/force-collection/REGTECH
# Health check
curl http://blacklist-collector:8545/health
```

## NOTES

- Communicates with `app/` via DB/Redis only. No code sharing.
- Tests: `tests/unit/collector/`, `tests/integration/collector/`
