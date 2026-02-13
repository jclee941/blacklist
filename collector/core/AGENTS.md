# COLLECTOR CORE KNOWLEDGE BASE

**Generated:** 2026-02-12
**Commit:** 83e7d28 | **Version:** 3.5.60
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
| Sync bulk HTTP | `aiohttp` + semaphore |

## COMPLEXITY HOTSPOTS

| File | Lines | Status |
|------|-------|--------|
| `fortigate_collector.py` | 680L | Active — consider splitting |
| `secudium_collector.py` | 676L | Active — manual OTP login flow added v3.5.55; consider splitting |

- v3.5.60: Resolved all 91 mypy type errors across 14 collector files (commit `83e7d28`)
