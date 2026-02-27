# EXCEPTIONS KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** d7bb4be
**Branch:** master | **Version:** 3.6.7

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

## CODE MAP

| Symbol                | Type  | Location                  | Refs | Role                                  |
| --------------------- | ----- | ------------------------- | ---- | ------------------------------------- |
| `BlacklistError`      | class | `base.py:9`               | high | root exception for all project errors |
| `APIError`            | class | `api_errors.py:62`        | high | RFC 7807 base (+status_code, +code)   |
| `ExternalAPIError`    | class | `api_errors.py:92`        | med  | external service failure wrapper      |
| `ValidationError`     | class | `validation_errors.py:8`  | high | 400 input validation                  |
| `NotFoundError`       | class | `validation_errors.py:48` | med  | 404 resource not found                |
| `DatabaseError`       | class | `infra_errors.py:35`      | med  | database operation failure            |
| `AuthenticationError` | class | `auth_errors.py:8`        | med  | auth flow failure                     |

## CONVENTIONS

- Only `APIError` subclasses produce RFC 7807 formatted JSON responses.
- Non-APIError exceptions caught by global handler → generic 500.
- 93 raise sites across 20 files.

## ANTI-PATTERNS

- Broad `BlacklistError` catch — use specific subclass.
- Manual error dict return — raise typed exception, let handler format RFC 7807.
- `raise Exception(...)` — use typed hierarchy.
- Catching `APIError` when you mean `ValidationError` (loses specificity).
