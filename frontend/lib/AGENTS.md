# FRONTEND LIB KNOWLEDGE BASE

## OVERVIEW

Centralized Axios API client. `lib/api.ts` exports exactly two instances (`api`, `collectionApi`) and is the single source of truth for browser HTTP calls.

## INSTANCES

| Instance        | Timeout | Use Case                           |
| --------------- | ------- | ---------------------------------- |
| `api`           | 60s     | default API calls                  |
| `collectionApi` | 420s    | long-running collection operations |

## AUTH

- JWT token stored in `localStorage` under `blacklist_auth_token`.
- Auto-attached to both instances via a shared Axios request interceptor.
- Login: `POST /api/auth/login`; Verify: `GET /api/auth/verify`.
- A 401 on any protected call clears the token and dispatches the `blacklist:auth-unauthorized` window event (`AUTH_UNAUTHORIZED_EVENT`); `components/AuthGate.tsx` listens for it and redirects to `/login`.

## BASE URL

Relative `/api/*` calls resolve differently per environment:

- Dev (`npm run dev`): `next.config.ts` rewrites `/api/:path*` to `NEXT_PUBLIC_API_URL` (default `http://localhost:2542`).
- Production (standalone build): `server.js`/`server-routing.js` proxy `/api/*` and `/health` straight to Flask; see `../AGENTS.md`.

## TESTING

- Unit tests live in `__tests__/lib/`: `api.test.ts` is the runner; `api-auth.cases.ts`, `api-endpoints.cases.ts`, and `api-interceptors.cases.ts` hold the shared case data; `api-test-helpers.ts` is the mock factory.
- Case modules export registration functions; do not rename those exports.

## ANTI-PATTERNS

- Direct `fetch()` calls in app runtime code; route requests through this client.
- Creating additional `axios.create()` instances.
- Ignoring rejected API promises; callers must handle API errors.
