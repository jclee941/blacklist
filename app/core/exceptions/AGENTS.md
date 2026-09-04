# EXCEPTIONS KNOWLEDGE BASE

## OVERVIEW

Typed exception hierarchy for RFC 7807 error responses. 8 modules under `app/core/exceptions/`.

## HIERARCHY

```
BlacklistError (base_exceptions.py): root, logs on construction
├── APIError (base_exceptions.py): +status_code, +error_code, RFC 7807 `to_api_response`
│   └── ExternalAPIError (base_exceptions.py) [502]
├── AuthenticationError, AuthorizationError (auth_exceptions.py)
├── CacheError, DatabaseError, ConnectionError (infrastructure_exceptions.py)
├── RateLimitError, ServiceUnavailableError, MonitoringError (service_exceptions.py)
├── DataProcessingError, DataError (data_exceptions.py)
└── ConfigurationError, DependencyError (config_exceptions.py)
```

`ValidationError`, `BadRequestError`, `NotFoundError`, `ConflictError`, `InternalServerError`, `UnauthorizedError`, `ForbiddenError` (all in `validation_exceptions.py`) extend `APIError` with RFC 7807 status codes 400/400/404/409/500/401/403.

Everything else above extends `BlacklistError` directly, isn't RFC 7807 shaped, and renders as a generic 500 through the global handler.

## CODE MAP

| Symbol                | Type  | Location                          | Refs | Role                                  |
| --------------------- | ----- | ---------------------------------- | ---- | ------------------------------------- |
| `BlacklistError`      | class | `base_exceptions.py`             | high | root exception for all project errors |
| `APIError`            | class | `base_exceptions.py`             | high | RFC 7807 base (+status_code, +error_code) |
| `ExternalAPIError`    | class | `base_exceptions.py`             | med  | external service failure wrapper (502) |
| `ValidationError`     | class | `validation_exceptions.py`       | high | 400 input validation                  |
| `NotFoundError`       | class | `validation_exceptions.py`       | med  | 404 resource not found                |
| `DatabaseError`       | class | `infrastructure_exceptions.py`   | med  | database operation failure            |
| `AuthenticationError` | class | `auth_exceptions.py`             | med  | auth flow failure                     |

## CONVENTIONS

- Only `APIError` subclasses produce RFC 7807 formatted JSON responses.
- Non-APIError exceptions caught by global handler → generic 500.
- Every raise is logged in `BlacklistError.__init__`; avoid raising in tight loops without rate limiting.

## ANTI-PATTERNS

- Broad `BlacklistError` catch — use specific subclass.
- Manual error dict return — raise typed exception, let handler format RFC 7807.
- `raise Exception(...)` — use typed hierarchy.
- Catching `APIError` when you mean `ValidationError` (loses specificity).
