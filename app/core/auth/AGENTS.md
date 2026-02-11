# AGENTS.md — JWT Authentication

**Generated:** 2026-02-11
**Commit:** 6cd4c24 | **Version:** 3.5.53
**Parent:** `app/core/` | **Total:** 163 lines (4 files)

## FILES

| File | Lines | Purpose |
|------|-------|---------|
| `jwt_service.py` | 65 | Token encode/decode — HS256, 8hr default expiry |
| `middleware.py` | 52 | `before_request` hook — enforces JWT on all routes |
| `decorators.py` | 30 | `@public` — marks endpoint as no-auth-required |
| `__init__.py` | 16 | Re-exports JWTService, AuthMiddleware, public |

## HOW IT WORKS

1. `AuthMiddleware.init_app(app)` registers `before_request` hook
2. Every request checked for `Authorization: Bearer <token>`
3. Routes decorated with `@public` skip check (`_public=True` on view func)
4. Token payload: `{sub: user_id, role: str, iat: int, exp: int}`
5. Decoded user set on `g.current_user`

## PUBLIC ENDPOINTS (no JWT)

`/health`, `/api/health`, `/metrics`, `/api/auth/login`, `/api/fortinet/threat-feed`, `/api/fortinet/json-connector`

## CRITICAL: MIDDLEWARE CURRENTLY DISABLED

Auth middleware registration is **commented out** at `app/run_app.py:156`. All routes currently accessible without JWT. This is a security gap.

## ANTI-PATTERNS

| Forbidden | Why |
|-----------|-----|
| Check auth manually in route | Use `@public` or rely on middleware |
| Store tokens in DB | Stateless JWT — no server-side sessions |
| Change algorithm from HS256 | Secret key management not set up for RSA |

## GAPS

- No token refresh mechanism
- No rate limiting on `/api/auth/login`
- No token revocation/blacklist
- Password hashing uses bcrypt but no password policy enforcement
