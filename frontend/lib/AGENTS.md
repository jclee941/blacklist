# FRONTEND LIB KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** cd16ec1
**Branch:** master | **Version:** 3.6.8

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

## CODE MAP

| Symbol          | Type     | Location    | Refs | Role                                                |
| --------------- | -------- | ----------- | ---- | --------------------------------------------------- |
| `collectionApi` | instance | `api.ts:33` | high | long-running collection Axios client (300s timeout) |
| `api`           | instance | `api.ts:*`  | high | default Axios client (60s timeout)                  |
| `getToken`      | function | `api.ts:7`  | high | JWT from localStorage                               |
| `login`         | function | `api.ts:63` | med  | POST /api/auth/login                                |
| `getStats`      | function | `api.ts:81` | med  | dashboard stats fetch                               |
