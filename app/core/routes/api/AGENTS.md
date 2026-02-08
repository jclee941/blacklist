# API ROUTES KNOWLEDGE BASE

**Generated:** 2026-02-08
**Commit:** 923a8ce
**Role:** JSON API Surface (Flask)
**Parent:** [../../AGENTS.md](../../AGENTS.md)

## OVERVIEW

JSON REST API layer. **Thin Handlers** — routes do validation/parsing → service call → response formatting only.

## STRUCTURE

```
api/
├── ip_management_api.py    # ⚠️ 1050L (IP CRUD/bulk) — needs splitting
├── system_api.py           # System status
├── dashboard_api.py        # Dashboard stats
├── analytics.py            # Analytics API
├── database_api.py         # DB utilities
├── migration.py            # Schema endpoints (sensitive)
├── collection/             # Collection control → delegates to collector
├── blacklist/              # Core threat intel
├── fortinet/               # FortiManager integration
└── monitoring/             # Monitoring/metrics
```

## HOW TO: Add Endpoint

1. Create `<feature>_api.py` with `Blueprint('<feature>_api', __name__, url_prefix='/api/<feature>')`
2. Use `current_app.extensions['<feature>_service']` for DI
3. Errors via `raise APIError("msg", status_code=404)` (RFC 7807)
4. Register in `app/core/app.py` → `app.register_blueprint(bp)`
5. Test in `tests/unit/app/routes/test_<feature>_api.py`

## KNOWN ISSUES

| Issue | Severity |
|-------|----------|
| `ip_management_api.py` 1050L monolith | HIGH — extract helpers |
| 10 unguarded `resp.json()` calls across routes | MEDIUM — add try/except |
| Hardcoded collector URL in `collection/utils.py:13` | MEDIUM — use env var |
| Hardcoded URL in `blacklist/collection.py:54` | MEDIUM — use env var |

## ANTI-PATTERNS

| Forbidden | Alternative |
|-----------|-------------|
| Business logic in routes | Delegate to service layer |
| `from core.services import X` | `current_app.extensions` |
| HTML responses in `/api/` | JSON only |
| Individual `jsonify` error dicts | `APIError` class |
