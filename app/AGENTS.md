# AGENTS.md — Flask API (`app/`)

**Generated:** 2026-02-11
**Commit:** 6cd4c24 | **Version:** 3.5.53
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
│   │   └── web/            # Jinja2 legacy admin → web/AGENTS.md
│   ├── database/           # Raw SQL infrastructure → database/AGENTS.md
│   ├── monitoring/         # Prometheus metrics → monitoring/AGENTS.md
│   └── utils/              # Shared utilities → utils/AGENTS.md
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

## COMPLEXITY HOTSPOTS

| File | Metric | Risk |
|------|--------|------|
| `core/app.py` | 39.91 complexity | HIGH |
| `services/blacklist_service.py` | 39.43 complexity | HIGH |

## NOTES

- Collection trigger: HTTP POST to collector or query `collection_history` table
- Three separate rate limiter instances exist (regtech, auth, Flask-Limiter) — consolidate
