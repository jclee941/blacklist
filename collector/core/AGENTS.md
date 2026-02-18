# COLLECTOR CORE KNOWLEDGE BASE

**Generated:** 2026-02-18
**Commit:** b5a2c7d | **Version:** 3.5.64
**Parent:** [../AGENTS.md](../AGENTS.md)

## OVERVIEW

Core ETL pipeline. Modular parsing + DB-based rate limiting + data normalization.

## STRUCTURE

```
core/
├── regtech/                   # Regtech collection package
│   ├── auth.py                # Multi-stage authentication (138L)
│   ├── collector.py           # Main collection logic (414L)
│   └── data_processor.py      # Data processing pipeline (331L)
├── multi_source/              # Multi-source collection package
│   ├── collector.py           # Async feed collection (408L)
│   ├── models.py              # Data models (47L)
│   └── parsers.py             # Feed-specific parsers (200L)
├── fortigate_collector.py     # FortiGate firewall data (680L)
├── secudium_collector.py      # Secudium threat intel (676L)
├── database.py                # Independent DB pool (maxconn=20)
├── authentication.py          # Fernet credential decryption
└── data_normalizer.py         # IP format standardization
```

## HOW TO: Add New Parser

1. Add parser function in appropriate module (`multi_source/parsers.py` or `regtech/data_processor.py`)
2. Call from collector (`parse_X(html) -> list[dict]`)
3. Store via `ON CONFLICT DO UPDATE` pattern

## CONVENTIONS

| Convention | Description |
|------------|-------------|
| Parsing separation | Parsing → separate modules, not in collectors |
| Rate limit | DB `SourceConfig`-based per-source intervals |
| Idempotency | `ON CONFLICT DO UPDATE` required |
| Error recovery | Exponential backoff (independent per-source failure) |

## ANTI-PATTERNS

| Forbidden | Alternative |
|-----------|-------------|
| Parsing logic in collectors | Separate parser modules |
| Direct DB writes (no transactions) | Transaction context |
| Hardcoded collection intervals | DB `SourceConfig` table |
| Shared mutable state without lock | `threading.Lock()` context manager |
| Sync bulk HTTP | `aiohttp` + semaphore |

## COMPLEXITY HOTSPOTS

| File | Lines | Status |
|------|-------|--------|
| `fortigate_collector.py` | 680L | Active — consider splitting |
| `secudium_collector.py` | 676L | Active — manual OTP login flow added v3.5.55; token lifecycle hardened v3.5.64 |

## SESSION MANAGEMENT SECURITY (v3.5.64)

### secudium_collector.py — Token Lifecycle

```python
_token_lock = threading.Lock()  # Class-level, protects ALL token access
_cached_token: Optional[str] = None
_token_expiry: Optional[float] = None
TOKEN_TTL = 4 * 3600        # 4 hours
TOKEN_SAFETY_MARGIN = 1800  # 30 minutes — re-auth before expiry
```

| Operation | Lock required | Method |
|-----------|---------------|--------|
| Token read | `_token_lock` | `_is_token_valid()` |
| Token write | `_token_lock` | `_authenticate()` |
| Token invalidate | `_token_lock` | `_invalidate_token()` |
| Duplicate login | Logout → re-auth (1 retry) | `_authenticate()` |

### database.py — IP Cache Eviction

- TTL: 24h, Max: 100K entries, LRU: oldest 10% evicted when over max
- Method: `DatabaseService._evict_stale_ips()`

## CHANGELOG

- v3.5.64: Token lifecycle hardening (TTL 4h, safety margin 30min, `_token_lock` on all access, duplicate login retry), IP cache eviction policy, dead code removal
- v3.5.60: Resolved all 91 mypy type errors across 14 collector files (commit `83e7d28`)
