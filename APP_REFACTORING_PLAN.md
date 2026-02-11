# Flask Application Refactoring Plan

**Target File:** `/home/jclee/dev/blacklist/app/core/app.py` (463 lines, complexity: 39.91)

## Problem Statement

The `create_app()` function is doing too much:
1. Security configuration (CSRF, rate limiting, headers)
2. Service initialization (DI container setup)
3. Blueprint registration (10+ API/web routes)
4. Health checks and background tasks
5. Middleware setup (request ID, gzip compression)

This violates the Single Responsibility Principle and makes testing difficult.

## Refactoring Strategy

Break `app.py` into **4 focused modules**:

### Module 1: `app/core/config/security.py` (NEW)
**Purpose:** Centralize security configuration

**Contents:**
- `UTF8JSONProvider` class
- `configure_security(app)` → returns (csrf, limiter)
- `add_security_headers(app)` → registers @after_request middleware

**Exports:**
```python
# In create_app():
from core.config.security import configure_security, add_security_headers
csrf, limiter = configure_security(app)
add_security_headers(app)
```

**Benefits:**
- Security configuration is testable
- Can be reused in test fixtures
- Separates concerns

### Module 2: `app/core/bootstrap/services.py` (NEW)
**Purpose:** Service initialization and DI setup

**Contents:**
- `initialize_services(app)` → initializes all 15 services
- Moved from `service_factory.py` initialization logic

**Exports:**
```python
# In create_app():
from core.bootstrap.services import initialize_services
services = initialize_services(app)
```

**Benefits:**
- Service init is isolated
- Testable independently
- Clear dependency order

### Module 3: `app/core/bootstrap/routes.py` (NEW)
**Purpose:** Centralize all blueprint registration

**Contents:**
- `register_api_blueprints(app, csrf)` — all API routes
- `register_web_blueprints(app, csrf)` — all web UI routes
- `register_error_handlers(app)` — error handlers
- `register_metrics(app)` — Prometheus metrics

**Exports:**
```python
# In create_app():
from core.bootstrap.routes import register_api_blueprints, register_web_blueprints
register_api_blueprints(app, csrf)
register_web_blueprints(app, csrf)
```

**Benefits:**
- Route registration is centralized
- Easy to add/remove routes
- Clear dependency on csrf

### Module 4: `app/core/bootstrap/health.py` (NEW)
**Purpose:** Health checks and background tasks

**Contents:**
- `health_check()` — moved endpoint
- `start_background_tasks()` — background scheduler
- `setup_health_and_tasks(app)` — registration function

**Exports:**
```python
# In create_app():
from core.bootstrap.health import setup_health_and_tasks
setup_health_and_tasks(app)
```

**Benefits:**
- Health logic is isolated
- Background tasks can be mocked in tests
- Clear lifecycle management

---

## Refactored `create_app()` Structure

**Before (463 lines):**
```python
def create_app():
    app = Flask(__name__)
    # ... 400+ lines of mixed concerns
    return app
```

**After (~80-100 lines):**
```python
from pathlib import Path
from flask import Flask, g, uuid
from core.config.security import configure_security, add_security_headers
from core.bootstrap.services import initialize_services
from core.bootstrap.routes import register_api_blueprints, register_web_blueprints
from core.bootstrap.health import setup_health_and_tasks

def create_app():
    """Create Flask application with modular configuration"""
    # 1. Initialize Flask app
    app_root = Path(__file__).parent.parent
    app = Flask(__name__, template_folder=str(app_root / "templates"))

    # 2. Security
    csrf, limiter = configure_security(app)
    add_security_headers(app)

    # 3. Services (DI)
    initialize_services(app)

    # 4. Request tracking middleware
    @app.before_request
    def generate_request_id():
        g.request_id = str(uuid.uuid4())

    # 5. Compression
    @app.after_request
    def compress_response(response):
        # ... compression logic moved to helper
        pass

    # 6. API & Web routes
    register_api_blueprints(app, csrf)
    register_web_blueprints(app, csrf)

    # 7. Health & background tasks
    setup_health_and_tasks(app)

    return app
```

**Benefits:**
- ✅ Each module has single responsibility
- ✅ Testable in isolation
- ✅ Easy to understand flow
- ✅ Can reorder init phases without side effects
- ✅ ~80% complexity reduction
- ✅ Easier to maintain and extend

---

## Implementation Steps

### Step 1: Create directory structure
```bash
mkdir -p app/core/config
mkdir -p app/core/bootstrap
touch app/core/config/__init__.py
touch app/core/bootstrap/__init__.py
```

### Step 2: Create modules (in order)
1. `app/core/config/security.py` — extract security code
2. `app/core/bootstrap/services.py` — extract service init
3. `app/core/bootstrap/routes.py` — extract route registration
4. `app/core/bootstrap/health.py` — extract health/tasks

### Step 3: Update `app/core/app.py`
- Replace implementation with imports and modular calls
- Keep same public API (`create_app()`)
- No breaking changes to callers

### Step 4: Testing
- Add unit tests for each module:
  - `tests/unit/app/core/config/test_security.py`
  - `tests/unit/app/core/bootstrap/test_services.py`
  - `tests/unit/app/core/bootstrap/test_routes.py`
  - `tests/unit/app/core/bootstrap/test_health.py`

### Step 5: Verify
- Run existing tests: `make test`
- Check app startup: `make dev-app`
- Verify metrics: `curl http://localhost:2542/metrics`
- Verify health: `curl http://localhost:2542/health`

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Import cycles | Keep modules independent; avoid cross-imports |
| Test failures | Run full test suite after refactor |
| Startup regression | Verify with `make dev-app` |
| Order dependencies | Document init order in `bootstrap/__init__.py` |

---

## Expected Outcomes

- **Complexity Reduction:** 39.91 → ~15-18 (60% reduction)
- **Testability:** Security, services, routes each testable independently
- **Maintainability:** Clear separation of concerns
- **Code Reuse:** Modules can be imported in tests
- **No Breaking Changes:** Same `create_app()` API

---

## Compression Feature (Refactoring Opportunity)

Current compression is in `create_app()` as after_request middleware.
Can be moved to `app/core/utils/compression.py`:

```python
# app/core/utils/compression.py
def setup_gzip_compression(app: Flask) -> None:
    """Setup Gzip compression with smart heuristics"""
    @app.after_request
    def compress_response(response):
        # ... compression logic
        pass
```

Then in refactored app:
```python
from core.utils.compression import setup_gzip_compression
setup_gzip_compression(app)
```

---

## Files to Create

```
app/core/
├── config/
│   ├── __init__.py (NEW)
│   └── security.py (NEW, ~150 lines)
├── bootstrap/
│   ├── __init__.py (NEW)
│   ├── services.py (NEW, ~30 lines, mostly calls)
│   ├── routes.py (NEW, ~200 lines)
│   └── health.py (NEW, ~100 lines)
└── utils/
    └── compression.py (NEW, ~50 lines)
```

**Total new code:** ~550 lines (extracted from app.py)
**Reduced app.py:** 463 → ~80-100 lines

---

## Backwards Compatibility

✅ **FULL COMPATIBILITY**
- `create_app()` function signature unchanged
- All existing imports work
- No changes needed in `run_app.py`
- Tests use same `create_app()` fixture

---

## Next Steps After Refactoring

1. **Refactor `blacklist_service.py`** (complexity: 39.43)
   - Similar modularization strategy
   - Extract IP filtering logic to separate classes
   - Extract caching logic to separate service

2. **Add comprehensive unit tests**
   - Each refactored module gets tests
   - Integration tests for bootstrap flow
   - Test service initialization order

3. **Document module interactions**
   - Create `app/core/ARCHITECTURE.md`
   - Document DI container flow
   - Document request flow through middleware

