# FRONTEND LIB KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** cd16ec1
**Branch:** master | **Version:** 5.0.0

## OVERVIEW

Centralized Axios API client. Single source of truth for all HTTP communication.

## INSTANCES

| Instance        | Timeout | Use Case                           |
| --------------- | ------- | ---------------------------------- |
| `api`           | 60s     | default API calls                  |
| `collectionApi` | 420s    | long-running collection operations |

## AUTH

- JWT token from `localStorage` key `blacklist_auth_token`.
- Auto-attached via Axios request interceptor.
- Login: `POST /api/auth/login`
- Verify: `GET /api/auth/verify`
- Protected 401 responses clear the token and dispatch `blacklist:auth-unauthorized`;
  `AuthGate` subscribes to this event.

## BASE URL

Relative `/api/*` → Next.js rewrites to `NEXT_PUBLIC_API_URL` (default
`http://localhost:2542`, configured in `next.config.ts`).

## TESTING

- Unit tests live in `__tests__/lib/`: `api.test.ts` (runner) + `api-auth/endpoints/interceptors.cases.ts` (shared case data) + `api-test-helpers.ts` (mock factory).
- Case modules export registration functions; do not rename exports.

## ANTI-PATTERNS

- Direct `fetch()` calls in app runtime code; route requests through this client.
- Creating additional `axios.create()` instances.
- Ignoring rejected API promises; callers must handle API errors.
