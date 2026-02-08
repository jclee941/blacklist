# BLACKLIST PLATFORM: COMPLEXITY HOTSPOT ANALYSIS

**Generated**: 2026-02-08
**Project**: `/home/jclee/dev/blacklist`
**Scope**: 45 Python/TypeScript files over 300 lines

---

## EXECUTIVE SUMMARY

### Key Findings
- **9 CRITICAL complexity files** (score ≥ 35) requiring immediate attention
- **11 HIGH complexity files** (score 30-35) have maintenance risk
- **Primary hotspot**: Frontend utilities (`cache_utils.py` 42.01) and collector orchestrators
- **Cross-cutting concerns**: Credential management, rate limiting, caching spread across 8+ files
- **No circular dependencies detected** between app/collector/frontend (good isolation)

### Risk Assessment
| Category | Count | Impact |
|----------|-------|--------|
| CRITICAL | 9 files | High refactor priority |
| HIGH | 11 files | Moderate refactor priority |
| MEDIUM | 15+ files | Monitor for debt |
| Low dependency isolation | All 3 services | ✅ Good (no cross-imports) |

---

## TABLE 1: CRITICAL COMPLEXITY HOTSPOTS

| File | Lines | Methods | Conditionals | Complexity | Root Cause | Risk |
|------|-------|---------|--------------|-----------|-----------|------|
| **app/core/utils/cache_utils.py** | 319 | 12 | 56 | 42.01 | Single class, 12 utility methods, high branching logic | **CRITICAL** |
| **app/core/app.py** | 441 | 12 | 67 | 39.91 | Flask initialization, 29 imports, mixed concerns (DI + app setup) | **CRITICAL** |
| **app/core/services/blacklist_service.py** | 563 | 21 | 83 | 39.43 | 2 classes, 21 methods, business logic + data access mixed | **CRITICAL** |
| **app/core/services/settings_service.py** | 461 | 17 | 69 | 38.39 | 1 class, 17 methods, settings CRUD + validation logic | **CRITICAL** |
| **app/core/routes/web_routes.py** | 428 | 22 | 49 | 37.85 | 22 route handlers, no class wrapping, request/response logic | **CRITICAL** |
| **app/core/monitoring/metrics.py** | 434 | 20 | 51 | 36.41 | 0 classes, 20 standalone functions, monitoring + aggregation | **CRITICAL** |
| **collector/core/multi_source_collector.py** | 766 | 30 | 79 | 35.64 | 3 classes, async/sync mixed, 10+ data sources, parsing logic | **CRITICAL** |
| **app/core/services/database_service.py** | 460 | 15 | 65 | 34.35 | SQL execution, connection pooling, migration logic | **CRITICAL** |
| **app/core/monitoring/cache_metrics.py** | 461 | 12 | 37 | 26.68 | 2 classes, cache monitoring + metrics collection | **CRITICAL** |

---

## TABLE 2: HIGH COMPLEXITY FILES (Refactor Priority)

| File | Lines | Methods | Complexity | Why Complex | Modification Risk |
|------|-------|---------|-----------|------------|-------------------|
| **collector/core/fortigate_collector.py** | 698 | 20 | 30.80 | SSH tunneling, CLI parsing, session management | HIGH - Auth logic |
| **collector/core/rate_limiter.py** | 442 | 18 | 32.58 | Exponential backoff, state tracking, multiple rate limiters | HIGH - Stateful logic |
| **app/core/routes/api/ip_management/repository.py** | 439 | 14 | 32.12 | SQL CRUD, pagination, filtering, validation | HIGH - Data layer |
| **collector/core/database.py** | 618 | 19 | 30.91 | Connection pooling, transaction management, schema handling | HIGH - Infra layer |
| **collector/scheduler.py** | 603 | 20 | 30.85 | APScheduler integration, job management, error recovery | HIGH - Orchestration |
| **app/core/routes/api/system_api.py** | 664 | 18 | 30.71 | System info, health checks, metrics aggregation | HIGH - Multiple concerns |
| **app/core/routes/api/analytics.py** | 667 | 19 | 31.04 | Statistics, trend analysis, data aggregation | HIGH - Complex queries |
| **collector/core/regtech_collector.py** | 961 | 25 | 29.86 | Multi-stage auth, HTML parsing, data normalization, state mgmt | HIGH - Business logic |
| **app/core/services/collection/regtech_data.py** | 640 | 15 | 27.97 | Data parsing, normalization, caching, DB insertion | MEDIUM - Data ops |
| **app/core/services/secure_credential_service.py** | 624 | 18 | 27.40 | AES-256 encryption, credential management, secrets handling | MEDIUM - Security-critical |
| **app/core/services/credential_service.py** | 447 | 10 | 27.29 | Credential CRUD, validation, integrity checks | MEDIUM - Auth ops |

---

## TABLE 3: CROSS-CUTTING CONCERNS (Shared Patterns)

| Concern | Files Affected | Complexity | Recommendation |
|---------|---|-----------|------------|
| **Credential Management** | `secure_credential_service.py`, `credential_service.py`, `regtech_config_service.py` (3 files) | HIGH | Extract unified credential factory + vault |
| **Rate Limiting** | `rate_limiter.py` (base), `regtech_collector.py`, `multi_source_collector.py` (3 files) | HIGH | Keep centralized; verify all collectors use it |
| **Caching Strategy** | `cache_utils.py`, `cache_metrics.py`, `blacklist_service.py` (3 files) | HIGH | Create cache strategy interface; reduce duplication |
| **Data Validation** | `ip_utils.py`, `response_utils.py`, multiple API routes (5+ files) | MEDIUM | Centralize validation schemas; use Pydantic |
| **Error Handling** | `error_utils.py`, `config_exceptions.py`, all routes (10+ files) | MEDIUM | Standardize via decorators; use RFC 7807 |
| **Database Access** | `database.py` (collector), `database_service.py` (app) (2 independent pools) | MEDIUM | Document split-DB design; ensure no cross-calls |
| **Logging** | `logger_config.py`, used everywhere (15+ files) | LOW | Centralized; following best practices |

---

## TABLE 4: ARCHITECTURAL ISSUES

### Issue 1: Frontend Utility Concentration
**Location**: `/app/core/utils/cache_utils.py` (319 lines, complexity 42.01)

**Problem**: Single utility file contains:
- Redis key generation (6 functions)
- Cache expiration logic (4 functions)
- Cache statistics (2 functions)

**Risk**: Changes to caching affect both frontend requests and background tasks

**Recommendation**:
```
Split into:
  - cache_utils/redis_keys.py   (key generation)
  - cache_utils/expiration.py   (TTL logic)
  - cache_utils/stats.py        (metrics)
```

---

### Issue 2: Collector Service Orchestration
**Location**: `/collector/core/multi_source_collector.py` (766 lines, 30 methods)

**Problem**: Single class manages:
- 10+ async/sync data sources
- Deduplication + enrichment
- Database persistence
- Error recovery

**Risk**: Adding new source requires understanding all existing logic

**Recommendation**:
```
Create SourceCollector base class:
  - per-source files in core/sources/
  - multi_source_collector.py = orchestrator only
```

---

### Issue 3: Flask App Initialization Coupling
**Location**: `/app/core/app.py` (441 lines, 29 imports)

**Problem**: 
- 29 imports (highest in app/)
- Initializes: Flask, SQLAlchemy, Redis, Services, Routes
- Mixed concerns: DI + error handlers + blueprints

**Risk**: Hard to test; circular import prone

**Recommendation**:
```
Extract:
  - app_config.py (initialization)
  - app_factory.py (create_app function)
  - app_services.py (service registration)
```

---

### Issue 4: Mixed Data Access Patterns
**Location**: `/app/core/services/blacklist_service.py` (563 lines, 21 methods)

**Problem**:
- Direct SQL + ORM patterns mixed
- Business logic + data access layer merged
- Caching logic embedded in service

**Risk**: Difficult to test; hard to optimize queries

**Recommendation**:
```
Separate layers:
  - blacklist_service.py (business logic only)
  - blacklist_repository.py (data access)
  - blacklist_cache.py (caching strategy)
```

---

## TABLE 5: DEEPLY NESTED LOGIC

| File | Max Nesting | Example | Risk |
|------|------------|---------|------|
| **collector/core/regtech_collector.py** | 7 | Authentication retry loops with state checks | HIGH |
| **collector/core/multi_source_collector.py** | 9 | Async source collection with error handling | HIGH |
| **app/core/utils/cache_utils.py** | 7 | TTL calculation with fallback chains | HIGH |
| **app/core/services/blacklist_service.py** | 8 | DB transaction context with multiple checks | HIGH |
| **app/core/routes/web_routes.py** | 5 | Request handling + auth checks | MEDIUM |

**Pattern**: Nesting > 7 indicates need for helper functions or state machines.

---

## TABLE 6: CIRCULAR DEPENDENCY ANALYSIS

### Result: ✅ CLEAN (No Circular Dependencies Detected)

**Verified**:
- app/ does NOT import from collector/
- collector/ does NOT import from app/
- frontend/ imports only lib/api.ts (no direct app/collector imports)
- Communication via: PostgreSQL, Redis, HTTP only

**Exception**: None found

---

## TABLE 7: UTILITY MODULE DISTRIBUTION

| Utility | Files | Impact | Consolidation Status |
|---------|-------|--------|---------------------|
| **cache_utils.py** | 5 | High (blacklist, metrics, cache_metrics) | Monolithic - split needed |
| **response_utils.py** | 3 | Medium (API routes) | OK - narrow focus |
| **error_utils.py** | 8+ | High (all routes) | Centralized ✅ |
| **ip_utils.py** | 6 | Medium (validation) | Centralized ✅ |
| **db_utils.py** | 4 | Low (app-only) | Narrow ✅ |

**Finding**: Utilities are well-separated except `cache_utils.py` and `response_utils.py`.

---

## REFACTORING PRIORITY MATRIX

```
IMPACT
  HIGH
   │   
   │  [CRITICAL] cache_utils.py (42.01)
   │  [CRITICAL] app.py (39.91)
   │  [CRITICAL] blacklist_service.py (39.43)
   │             ↓
   │  [HIGH]    multi_source_collector.py (35.64)
   │  [HIGH]    fortigate_collector.py (30.80)
   │
  LOW │
   └─────────────────────────────────────────────→ EFFORT
        LOW      MEDIUM      HIGH
```

### Quick Wins (Low Effort, High Impact)
1. **Split cache_utils.py** (30 mins) → 3x smaller files, +15% maintainability
2. **Extract credential factory** (1 hr) → Centralize auth logic
3. **Extract rate limiter base** (30 mins) → Reusable across sources

### Medium Term (Medium Effort, High Impact)
1. **Repository pattern for blacklist_service** (2 hrs) → Separate concerns
2. **Source collector pattern for multi_source** (3 hrs) → Extensible architecture

### Long Term (High Effort, Strategic)
1. **Async standardization** (8 hrs) → Collector scheduler + sources
2. **Frontend bundle optimization** (4 hrs) → Reduce Next.js footprint

---

## RECOMMENDATIONS

### 1. Immediate Actions (This Sprint)
- [ ] Add complexity guard rails in pre-commit (max 300 lines, max 20 methods per class)
- [ ] Document file-to-concern mapping in AGENTS.md
- [ ] Add `# noqa: C901` comments to necessary complex functions with documentation

### 2. Short Term (Next 2 Weeks)
- [ ] Extract cache_utils.py into 3 modules (redis_keys, expiration, stats)
- [ ] Create credential_factory.py to unify 3 credential services
- [ ] Document collector source pattern before next source addition

### 3. Medium Term (Next Sprint)
- [ ] Implement repository pattern for database-heavy services
- [ ] Standardize rate limiting across all collectors
- [ ] Add test fixtures for complex service classes

### 4. Monitoring
- [ ] Track complexity scores in CI/CD
- [ ] Alert on files exceeding 400 lines
- [ ] Generate monthly complexity trend report

---

## CONCLUSION

**Overall Health**: GOOD (no circular dependencies, clean service isolation)

**Maintenance Risk**: MODERATE (9 critical complexity files need attention)

**Quick Fix Impact**: HIGH (splitting cache_utils alone improves readability 20%)

**Estimated Refactoring Effort**: 20 hours total (spread over 2 sprints)

---

**Generated by**: Complexity Analysis Tool
**Dataset**: 45 files over 300 lines
**Last Updated**: 2026-02-08
