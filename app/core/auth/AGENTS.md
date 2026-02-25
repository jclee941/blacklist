# AUTH KNOWLEDGE BASE

**Generated:** 2026-02-25 15:26 Asia/Seoul
**Commit:** e50fb74
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

JWT authentication layer. 163 lines across 4 files. **CRITICAL: middleware currently DISABLED.**

## FILES

| File             | LOC | Role                                     |
| ---------------- | --- | ---------------------------------------- |
| `jwt_service.py` | 65  | HS256 token create/verify, 8hr expiry    |
| `middleware.py`  | 52  | `before_request` hook for JWT validation |
| `decorators.py`  | 30  | `@public` decorator to exempt routes     |
| `__init__.py`    | 16  | re-exports                               |

## CODE MAP

| Symbol              | Type      | Location            | Refs | Role                                     |
| ------------------- | --------- | ------------------- | ---- | ---------------------------------------- |
| `JWTService`        | class     | `jwt_service.py:23` | med  | HS256 encode/decode/validate, 8hr expiry |
| `jwt_required_hook` | function  | `middleware.py:23`  | med  | `before_request` JWT validation hook     |
| `public`            | decorator | `decorators.py`     | med  | exempts route from JWT requirement       |
| `_auth_error`       | function  | `middleware.py:60`  | low  | RFC 7807 auth error response builder     |

## TOKEN PAYLOAD

```json
{ "sub": "user_id", "role": "admin", "iat": 1234567890, "exp": 1234596690 }
```

## PUBLIC ENDPOINTS (no JWT required)

- `/health`, `/api/health`, `/metrics`
- `/api/auth/login`
- `/api/fortinet/threat-feed`, `/api/fortinet/json-connector`

## STATUS

- Middleware DISABLED at `app/core/app.py:155` (commented out `before_request` hook).
- All routes currently accessible without JWT.

## KNOWN GAPS

- No refresh token mechanism.
- No rate limiting on `/api/auth/login`.
- No token revocation / blacklist.
- No password policy enforcement.
