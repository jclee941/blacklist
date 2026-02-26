# FRONTEND KNOWLEDGE BASE

**Generated:** 2026-02-26 00:00 Asia/Seoul
**Commit:** 803209d
**Branch:** master | **Version:** 3.6.4

## OVERVIEW

Next.js 15 + React 19 admin dashboard. Tailwind v4 + Radix UI + lucide-react + Recharts.

## STRUCTURE

```text
frontend/
├── app/
│   ├── page.tsx              # dashboard (554L)
│   ├── layout.tsx            # NavBar wrapper
│   ├── providers.tsx         # QueryClient provider
│   ├── ip-management/        # IP management client + components/ + hooks/
│   ├── collection/           # CollectionManagementClient + components/ + hooks/
│   ├── analytics/            # analytics page (273L)
│   ├── database/             # DB admin page
│   ├── fortinet/             # Fortinet management
│   └── settings/             # settings page (421L)
├── components/ui/            # 9 shared components
├── lib/                      # API client (centralized Axios)
├── hooks/                    # shared React hooks
├── types/                    # TypeScript type definitions
├── e2e/                      # Playwright E2E tests
├── __tests__/                # Vitest unit tests
├── next.config.ts            # API rewrites /api/* → :2542, standalone output
└── playwright.config.ts      # E2E configuration
```

## WHERE TO LOOK

| Task              | Location         | Notes                            |
| ----------------- | ---------------- | -------------------------------- |
| API client        | `lib/api.ts`     | REQUIRED for all API calls       |
| Shared components | `components/ui/` | Button, Card, Modal, Tabs, etc.  |
| State management  | React Query      | Zustand in deps but unused       |
| API proxy config  | `next.config.ts` | `/api/*` rewrites to Flask :2542 |

## CONVENTIONS

- API calls: `lib/api.ts` only — no direct `fetch()` in app code.
- Server + Client component split (Next.js App Router).
- Styling: Tailwind only, no CSS modules.
- State: React Query (server state) + useState (client state). Zustand declared but unused.
- Standalone output for Docker deployment.

## ANTI-PATTERNS

- Direct `fetch()` calls bypassing `lib/api.ts`.
- Creating additional `axios.create()` instances.
- Direct DB calls from frontend (use HTTP API boundary).

## KNOWN ISSUES

- Dashboard and management pages (`app/page.tsx`, `app/ip-management/*`, `app/collection/*`) remain complexity hotspots.
- Dual polling pattern remains in selected pages (interval + query refetch overlap).
- Hardcoded API URL in `next.config.ts`.

## TESTING

- Unit: Vitest (`__tests__/`)
- E2E: Playwright (`e2e/`), 60s timeout, multi-browser snapshots.

## CODE MAP

| Symbol           | Type   | Location         | Refs | Role                                     |
| ---------------- | ------ | ---------------- | ---- | ---------------------------------------- |
| `next.config.ts` | config | `next.config.ts` | high | API proxy rewrites /api/\* → Flask :2542 |

Page component CODE MAP in `app/AGENTS.md`. API client CODE MAP in `lib/AGENTS.md`.
