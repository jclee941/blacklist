# FRONTEND LIB KNOWLEDGE BASE

## OVERVIEW

Centralized Axios API client. `lib/api.ts` exports exactly two instances (`api`, `collectionApi`) and is the single source of truth for browser HTTP calls.

## INSTANCES

| Instance        | Timeout | Use Case                           |
| --------------- | ------- | ---------------------------------- |
| `api`           | 60s     | default API calls                  |
| `collectionApi` | 420s    | long-running collection operations |

## AUTH

- The JWT lives in the `blacklist_auth` HttpOnly cookie issued by `POST /api/auth/login`; browser code never reads or stores it, and both instances set `withCredentials: true` so it rides along on same-origin calls.
- No request interceptor attaches an `Authorization` header — that header path stays for non-browser API clients.
- Login: `POST /api/auth/login`; Verify: `GET /api/auth/verify`; Logout: `POST /api/auth/logout` clears the cookie server-side.
- A 401 on any protected call dispatches the `blacklist:auth-unauthorized` window event (`AUTH_UNAUTHORIZED_EVENT`); `components/AuthGate.tsx` listens for it and redirects to `/login`. `AuthGate` asks the server (`verifyToken`) whether the session is valid, since the cookie is invisible to JavaScript.

## BASE URL

Relative `/api/*` calls resolve differently per environment:

- Dev (`npm run dev`): `next.config.ts` rewrites `/api/:path*` to `NEXT_PUBLIC_API_URL` (default `http://localhost:2542`).
- Production (standalone build): `server.js`/`server-routing.js` proxy `/api/*` and `/health` straight to Flask; see `../AGENTS.md`.

## TESTING

- Unit tests live in `__tests__/lib/`: `api.test.ts` is the runner; `api-auth.cases.ts`, `api-endpoints.cases.ts`, and `api-interceptors.cases.ts` hold the shared case data; `api-test-helpers.ts` is the mock factory.
- Case modules export registration functions; do not rename those exports.

## ANTI-PATTERNS

- Ignoring rejected API promises; callers must handle API errors.
