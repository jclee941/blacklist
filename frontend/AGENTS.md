# FRONTEND KNOWLEDGE BASE

## OVERVIEW

Next.js 15 + React 19 admin dashboard. Tailwind v4 + Radix UI + lucide-react + Recharts. Build output is `standalone`; `server.js` is the production entry point, not `next start`.

## STRUCTURE

```text
frontend/
├── app/                      # route pages, see app/AGENTS.md
├── components/ui/            # 9 shared components
├── lib/                      # API client (Axios), see lib/AGENTS.md
├── hooks/                    # shared React hooks
├── types/                    # TypeScript type definitions
├── e2e/                      # Playwright specs, see e2e/AGENTS.md
├── __tests__/                # Vitest specs, see __tests__/AGENTS.md
├── server.js                 # production HTTPS/HTTP server + Flask proxy (standalone runtime)
├── server-routing.js         # proxy/static/security-header helpers used by server.js
├── next.config.ts            # dev-server rewrites, redirects, security headers
└── playwright.config.ts      # E2E configuration
```

## WHERE TO LOOK

| Task                      | Location                         | Notes                                                                                  |
| ------------------------- | -------------------------------- | -------------------------------------------------------------------------------------- |
| API client                | `lib/api.ts`                     | required for all browser API calls                                                     |
| Shared components         | `components/ui/`                 | Button, Card, Modal, Tabs, etc.                                                        |
| State management          | React Query                      | Zustand in deps but unused                                                             |
| Production proxy/security | `server.js`, `server-routing.js` | HTTPS proxy to Flask, static path-traversal guard, request body cap, forwarded headers |
| Dev-server API rewrites   | `next.config.ts`                 | used only by `npm run dev`; production traffic runs through `server.js` instead        |

## CONVENTIONS

- API calls: `lib/api.ts` only, no direct `fetch()` in app code.
- Server + Client component split (Next.js App Router).
- Styling: Tailwind only, no CSS modules.
- State: React Query (server state) + useState (client state). Zustand is declared but unused.
- `npm run build` produces standalone output; `server.js` runs it in Docker, `next dev` runs against `next.config.ts` locally.

## ANTI-PATTERNS

- Direct `fetch()` calls bypassing `lib/api.ts`.
- Creating additional `axios.create()` instances.
- Direct DB calls from frontend (use the HTTP API boundary).
- Editing `next.config.ts` rewrite rules and expecting them to change production proxy behavior; that's owned by `server-routing.js`.

## KNOWN ISSUES

- Dashboard and management pages (`app/page.tsx`, `app/ip-management/*`, `app/collection/*`) remain complexity hotspots.
- Dual polling pattern remains in selected pages (interval + query refetch overlap).

## TESTING

- Unit: Vitest, 46 files under `__tests__/`. Details in `__tests__/AGENTS.md`.
- E2E: Playwright, 27 spec files under `e2e/`. Details in `e2e/AGENTS.md`.

Page component CODE MAP in `app/AGENTS.md`. API client CODE MAP in `lib/AGENTS.md`.
