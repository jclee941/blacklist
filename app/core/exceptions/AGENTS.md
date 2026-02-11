# AGENTS.md — Exception Hierarchy

**Generated:** 2026-02-11
**Commit:** 6cd4c24 | **Version:** 3.5.53
**Parent:** `app/core/` | **Total:** 619 lines (9 files)

## HIERARCHY

```
BlacklistError (base — all custom exceptions)
├── APIError (+status_code, +code → RFC 7807 JSON response)
│   ├── ValidationError [400]
│   ├── BadRequestError [400]
│   ├── NotFoundError [404]
│   ├── ConflictError [409]
│   ├── InternalError [500]
│   ├── UnauthorizedError [401]
│   └── ForbiddenError [403]
├── AuthenticationError
├── RateLimitError
├── ServiceUnavailableError
├── DataError
├── ConfigurationError
├── CacheError
├── DatabaseError
└── ConnectionError
```

## KEY FILES

| File | Lines | Purpose |
|------|-------|---------|
| `base.py` | 45 | `BlacklistError` base class |
| `api_errors.py` | 180 | `APIError` + HTTP subclasses — RFC 7807 serialization |
| `handlers.py` | 95 | Flask `errorhandler` registrations |
| `__init__.py` | 42 | Re-exports all exception classes |

## USAGE PATTERN

```python
from app.core.exceptions import NotFoundError, ValidationError

raise NotFoundError(message="IP not found", code="NOT_FOUND_IP")
raise ValidationError(message="Invalid CIDR", code="VALID_CIDR")
```

**93 raise sites** across 20 files. Code prefixes: `AUTH_`, `VALID_`, `NOT_FOUND_`, `INTERNAL_`.

## RFC 7807 — APIError SUBCLASSES ONLY

Only `APIError` and its subclasses produce RFC 7807 JSON. Other `BlacklistError` subclasses (DatabaseError, CacheError, etc.) are caught by `handlers.py` and wrapped into generic 500 responses.

## ANTI-PATTERNS

| Forbidden | Why |
|-----------|-----|
| `raise Exception("...")` | Use typed exception from hierarchy |
| Catch `BlacklistError` broadly | Catch specific subclass |
| Return error dict manually | Raise exception — handler formats response |
