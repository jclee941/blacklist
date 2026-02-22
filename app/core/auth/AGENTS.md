# AUTH KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
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
