# AGENTS.md — Flask API (`app/`)

**Generated:** 2026-02-08
**Commit:** 450d20c | **Version:** 3.5.39
**Parent:** [../AGENTS.md](../AGENTS.md)

## STRUCTURE

```
app/
├── run_app.py              # Entry point (:2542)
├── core/
│   ├── app.py              # Application Factory (complexity: 39.91)
│   ├── services/           # 16+ services → services/AGENTS.md
│   │   └── service_factory.py  # DI container (init order matters)
│   ├── routes/
│   │   ├── api/            # JSON API (RFC 7807) → api/AGENTS.md
│   │   │   └── ip_management/  # Refactored subpackage (v3.5.37)
│   │   └── web/            # Jinja2 legacy admin
│   ├── database/           # Raw SQL infrastructure
│   └── utils/
│       └── cache_utils.py  # Complexity: 42.01 — highest in project
├── templates/              # Jinja2 (legacy, minimize changes)
└── static/                 # Static assets (legacy)
```

## HOW TO: Add API Endpoint

```python
# 1. core/routes/api/my_feature_api.py
bp = Blueprint('my_feature', __name__, url_prefix='/api/my-feature')

@bp.route('/', methods=['GET'])
def list_items():
    svc = current_app.extensions['my_service']  # MANDATORY DI pattern
    return jsonify({'items': svc.get_all()})

# 2. Register in core/routes/__init__.py → register_blueprints()
# 3. If new service needed → see services/AGENTS.md
```

## ANTI-PATTERNS

| Forbidden | Use Instead |
|-----------|-------------|
| `from app.core.services import X` | `current_app.extensions['x']` |
| `BlacklistService()` | ServiceFactory DI |
| `from run_app import app` | `current_app` proxy |
| SQL string concatenation | Parameterized `%s` queries |
| `resp.json()` without guard | `try/except` or status check first |

## KNOWN ISSUES

### DI Violations (3 files)
`admin_routes.py`, `fortimanager_push_service.py`, `settings_service.py` directly instantiate services.

### Hardcoded URLs (5 violations)
| File | Line(s) |
|------|---------|
| `routes/api/collection/utils.py` | 13 |
| `routes/api/blacklist/collection.py` | 54 |
| `services/blacklist_service.py` | 420, 462, 510 |

Fix: use `COLLECTOR_URL` env var.

### Unguarded `.json()` Calls
~10 violations across route handlers. Always check `resp.status_code` before `.json()`.

### JWT Auth Not Enforced
Auth declared but no middleware validates tokens. Security risk.

## COMPLEXITY HOTSPOTS

| File | Metric | Risk |
|------|--------|------|
| `core/utils/cache_utils.py` | 42.01 complexity | HIGH |
| `core/app.py` | 39.91 complexity | HIGH |
| `services/blacklist_service.py` | 39.43 complexity | HIGH |
| `routes/api/ip_management/` | Refactored from 1050L monolith | ✅ RESOLVED |

## NOTES

- `app/core/collectors/` deleted — collection moved to `collector/` service
- Collection trigger: HTTP POST to collector or query `collection_history` table
- Three separate rate limiter instances exist (regtech, auth, Flask-Limiter) — consolidate
