# FRONTEND LIB KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

Centralized Axios API client (`api.ts`, 277L). Single source of truth for all HTTP communication.

## INSTANCES

| Instance        | Timeout | Use Case                           |
| --------------- | ------- | ---------------------------------- |
| `api`           | 60s     | default API calls                  |
| `collectionApi` | 300s    | long-running collection operations |

## AUTH

- JWT token from `localStorage` key `blacklist_auth_token`.
- Auto-attached via Axios request interceptor.
- Login: `POST /api/auth/login`
- Verify: `GET /api/auth/verify`

## BASE URL

Relative `/api/*` → Next.js rewrites to Flask `:2542` (configured in `next.config.ts`).

## ANTI-PATTERNS

- Direct `fetch()` calls anywhere in app code.
- Creating additional `axios.create()` instances.
- Skipping error handling on API responses.
