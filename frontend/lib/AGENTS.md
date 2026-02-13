# FRONTEND LIB KNOWLEDGE BASE

**Generated:** 2026-02-12  
**Commit:** 83e7d28 | **Version:** 3.5.60  
**Role:** API Client & Utilities  
**Parent:** ../AGENTS.md

## OVERVIEW

Centralized API client (Axios). ALL backend communication MUST go through `api.ts`.

**Two Axios instances:**

- `api` — general API calls (default timeout)
- `collectionApi` — ETL/collection calls (extended timeout for long-running operations)

**JWT**: Stored in `localStorage` key `blacklist_auth_token`. Auto-attached via Axios request interceptor as `Authorization: Bearer <token>`.

## WHERE TO LOOK

| If you need to…  | Go to…                |
| ---------------- | --------------------- |
| Make API calls   | `api.ts`              |
| Add new endpoint | `api.ts` (add method) |

## CONVENTIONS

- **Single Entry Point**: `api.ts` is the ONLY allowed way to call backend.
- **Proxy Path**: Requests go to `/api/*` (Next.js rewrites to Flask :2542).
- **Error Handling**: Use try/catch with typed error responses.
- **Auth/CSRF**: Handled automatically by Axios interceptors.

## ANTI-PATTERNS

| Forbidden                  | Why                               |
| -------------------------- | --------------------------------- |
| `fetch()` in components    | Bypasses error handling, CSRF     |
| `axios.create()` elsewhere | Must use `api` or `collectionApi` |
| Ignoring API errors        | Always handle with user feedback  |
