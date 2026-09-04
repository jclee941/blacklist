# AUTH KNOWLEDGE BASE

## OVERVIEW

JWT authentication layer. Global JWT enforcement is **active**: `app.before_request(jwt_required_hook)` runs on every request except static assets and `@public`-marked endpoints. Admin credential and session-version state live in `core/services/auth_state_service.py` (see `services/AGENTS.md`), not in this package.

## FILES

| File             | Role                                                                         |
| ---------------- | ---------------------------------------------------------------------------- |
| `security.py`    | bcrypt password hashing/policy, login lockout, JWT revocation store          |
| `jwt_service.py` | HS256 encode/decode/validate with `jti` + `session_version` claims           |
| `middleware.py`  | `before_request` hook enforcing JWT on all non-public routes                 |
| `proxy.py`       | `TrustedProxyMiddleware` — honors `X-Forwarded-*` only from trusted peers    |
| `feed.py`        | `feed_access_required` — Fortinet feed token + source-network check          |
| `decorators.py`  | `@public` decorator to exempt routes from JWT                                |
| `fortigate.py`   | `parse_fortigate_target` — validates FortiGate push target against allowlist |
| `__init__.py`    | re-exports `JWTService`, `jwt_required_hook`, `public`                       |

## CODE MAP

| Symbol                            | Type      | Location         | Refs | Role                                                              |
| --------------------------------- | --------- | ---------------- | ---- | ----------------------------------------------------------------- |
| `JWTService`                      | class     | `jwt_service.py` | high | HS256 encode/decode/validate, revocation + session-version checks |
| `jwt_required_hook`               | function  | `middleware.py`  | high | `before_request` JWT validation hook                              |
| `AuthSecurity`                    | class     | `security.py`    | med  | login lockout (5 failures/15min) + token revocation store         |
| `hash_password`/`verify_password` | function  | `security.py`    | med  | bcrypt hashing, 12-character/72-byte policy, legacy-hash upgrade  |
| `public`                          | decorator | `decorators.py`  | med  | exempts route from JWT requirement                                |
| `TrustedProxyMiddleware`          | class     | `proxy.py`       | med  | WSGI-level trusted-proxy header handling                          |
| `feed_access_required`            | decorator | `feed.py`        | low  | bearer-token + source-network guard for Fortinet feeds            |

## TOKEN PAYLOAD

```json
{
  "sub": "user_id",
  "role": "admin",
  "jti": "uuid",
  "session_version": 1,
  "iat": 1234567890,
  "exp": 1234596690
}
```

`session_version` is compared against `AuthStateService.current_session_version()` on every validation; rotating the admin password bumps the version and invalidates all prior tokens.

## PUBLIC ENDPOINTS (no JWT required)

- Path prefixes: `/static/`, `/favicon.ico`, `/robots.txt`.
- `@public`-decorated: `/health`, `/api/auth/login`, `/metrics`, `/api/fortinet/threat-feed`, `/api/fortinet/json-connector`, plus a few web-context health checks.

## CONVENTIONS

- `/api/auth/login` and `/api/auth/password` are both rate-limited (`5 per minute`) via `core/utils/rate_limit.py`.
- Login failures are tracked per `(username, client_ip)` and per-account in Redis via `AuthSecurity`; 5 failures locks for 15 minutes.
- Token revocation and session-version invalidation are the only logout/rotation mechanisms — there is no separate refresh-token flow.
