# FRONTEND LIB KNOWLEDGE BASE

**Generated:** 2026-02-11  
**Commit:** 6cd4c24 | **Version:** 3.5.53  
**Role:** API Client & Utilities  
**Parent:** ../AGENTS.md

## OVERVIEW

Centralized API client (Axios). ALL backend communication MUST go through `api.ts`.

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

| Forbidden                  | Why                              |
| -------------------------- | -------------------------------- |
| `fetch()` in components    | Bypasses error handling, CSRF    |
| `localhost:2542`           | Hardcoded port breaks deployment |
| `axios.create()` elsewhere | Must use shared instance         |
| Ignoring API errors        | Always handle with user feedback |
