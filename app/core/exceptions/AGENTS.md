# EXCEPTIONS KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

Typed exception hierarchy for RFC 7807 error responses. 619 lines across 9 files.

## HIERARCHY

```
BlacklistError (base)
└── APIError (+status_code, +code → RFC 7807 JSON)
    ├── ValidationError [400]
    ├── BadRequestError [400]
    ├── NotFoundError [404]
    ├── ConflictError [409]
    ├── UnauthorizedError [401]
    ├── ForbiddenError [403]
    └── InternalError [500]

Standalone (non-RFC 7807):
  AuthenticationError, RateLimitError, ServiceUnavailableError,
  DataError, ConfigurationError, CacheError, DatabaseError, ConnectionError
```

## CONVENTIONS

- Only `APIError` subclasses produce RFC 7807 formatted JSON responses.
- Non-APIError exceptions caught by global handler → generic 500.
- 93 raise sites across 20 files.

## ANTI-PATTERNS

- Broad `BlacklistError` catch — use specific subclass.
- Manual error dict return — raise typed exception, let handler format RFC 7807.
- `raise Exception(...)` — use typed hierarchy.
- Catching `APIError` when you mean `ValidationError` (loses specificity).
