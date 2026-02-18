# COLLECTOR KNOWLEDGE BASE

**Generated:** 2026-02-18
**Commit:** b5a2c7d | **Version:** 3.5.64
**Role:** ETL Service (Data Collection)
**Parent:** [../AGENTS.md](../AGENTS.md)

## OVERVIEW

Independent ETL service. Collects blacklists from external sources, normalizes, stores to DB.
Fully separated from `app/` — own DB pool, own process. Port 8545.

## STRUCTURE

```
run_collector.py        # Entry point (:8545)
config.py               # Environment config + credential cache
scheduler.py            # APScheduler-based scheduling
scheduler_api.py        # Collection trigger REST API
health_server.py        # K8s liveness/readiness + pending auth state
monitoring_scheduler.py # Monitoring schedule
fortimanager_uploader.py # FortiManager push (env-configurable URL)
core/                   # Collection logic (→ core/AGENTS.md)
  regtech/              # Regtech collection package
  multi_source/         # Multi-source collection package
utils/
  otp_email_reader.py   # IMAP OTP auto-reader (timeout-enforced)
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
| Shared mutable state without lock | `threading.Lock()` context manager | Race conditions |
| Unbounded caches/dicts | TTL + max size eviction | Memory leaks |
| Hardcoded URLs | `BLACKLIST_API_URL` env var / `_get_api_url()` | Deployment portability |
| Plaintext credentials in memory | `clear_credentials_cache()` after use | Security |
| IMAP without timeout | `IMAP4_SSL(timeout=30)` + `sock.settimeout()` | Hanging connections |

## SESSION MANAGEMENT (SECURITY)

### Thread Safety

All shared mutable state MUST be protected by locks:

```python
# health_server.py — pending auth state
with self._pending_auth_lock:
    self._secudium_pending_auth = {"collector": collector, ...}

# secudium_collector.py — token cache
with SecudiumCollector._token_lock:
    SecudiumCollector._cached_token = token
```

### Token Lifecycle (Secudium)

| Stage | Implementation | Location |
|-------|----------------|----------|
| Cache check | `_is_token_valid()` under `_token_lock` | L444-470 |
| TTL | 4h with 30min safety margin | L57-58 |
| Duplicate login recovery | Logout → re-auth (1 retry) | L336-364 |
| Cache invalidation | `_invalidate_token()` under `_token_lock` | L775+ |

### IP Cache Eviction

| Policy | Config | Default |
|--------|--------|---------|
| TTL | `ip_cache_ttl` | 86400s (24h) |
| Max size | `ip_cache_max_size` | 100,000 |
| LRU eviction | Oldest 10% when over max | Automatic |
| Method | `DatabaseService._evict_stale_ips()` | `core/database.py` |

### Credential Handling

```python
# After collection completes, clear cached credentials:
CollectorConfig.clear_credentials_cache()
```

### IMAP Timeout

```python
# OTPEmailReader enforces timeout at socket level:
self.imap = imaplib.IMAP4_SSL(server, timeout=30)  # Connection timeout
self.imap.sock.settimeout(30)  # Operation timeout
```

## KNOWN ISSUES

| Issue | Location | Severity | Status |
|-------|----------|----------|--------|
| ~~Hardcoded app URL~~ | `fortimanager_uploader.py` | ~~CRITICAL~~ | FIXED (env var) |
| `time.sleep()` blocking | `scheduler.py` | MEDIUM | Open |
| Single-stage Dockerfile | `Dockerfile` — Playwright bloat | MEDIUM | Open |

## COMMUNICATION

```bash
# Trigger collection
curl -X POST http://blacklist-collector:8545/api/force-collection/REGTECH
curl -X POST http://blacklist-collector:8545/api/force-collection/SECUDIUM
# Health check
curl http://blacklist-collector:8545/health
# Test authentication
curl -X POST http://blacklist-collector:8545/api/test-auth/secudium
```

## TESTS

- Unit: `tests/unit/collector/` — includes session management security suite (570 lines)
- Integration: `tests/integration/collector/`
- Security test suite: `test_session_management_security.py`
  - Pending auth concurrency (CRITICAL)
  - IP cache TTL + LRU eviction (HIGH)
  - Credential cleanup (HIGH)
  - IMAP timeout enforcement (MEDIUM)
  - FortiManager URL configuration (CRITICAL)
  - Integration: all locks + caches coexisting

## NOTES

- Communicates with `app/` via DB/Redis only. No code sharing.
- `BLACKLIST_API_URL` env var controls FortiManager push target (default: `http://blacklist-app:2542`)
