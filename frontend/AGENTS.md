# FRONTEND KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

## OVERVIEW

Next.js 15 + React 19 admin dashboard. Tailwind v4 + Radix UI + lucide-react + Recharts.

## STRUCTURE

```text
frontend/
├── app/
│   ├── page.tsx              # dashboard (554L)
│   ├── layout.tsx            # NavBar wrapper
│   ├── providers.tsx         # QueryClient provider
│   ├── ip-management/        # IPManagementClient (893L) + components/ + hooks/
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

| Task              | Location              | Notes                            |
| ----------------- | --------------------- | -------------------------------- |
| API client        | `lib/api.ts`          | REQUIRED for all API calls       |
| Shared components | `components/ui/`      | Button, Card, Modal, Tabs, etc.  |
| State management  | Zustand + React Query | per-page stores                  |
| API proxy config  | `next.config.ts`      | `/api/*` rewrites to Flask :2542 |

## CONVENTIONS

- API calls: `lib/api.ts` only — no direct `fetch()` in app code.
- Server + Client component split (Next.js App Router).
- Styling: Tailwind only, no CSS modules.
- State: Zustand (client state) + React Query (server state).
- Standalone output for Docker deployment.

## ANTI-PATTERNS

- Direct `fetch()` calls bypassing `lib/api.ts`.
- Creating additional `axios.create()` instances.
- Direct DB calls from frontend (use HTTP API boundary).

## KNOWN ISSUES

- `IPManagementClient.tsx` (893L) — complexity hotspot, candidate for decomposition.
- Dual polling pattern in some pages.
- Hardcoded API URL in `next.config.ts`.

## TESTING

- Unit: Vitest (`__tests__/`)
- E2E: Playwright (`e2e/`), 60s timeout, multi-browser snapshots.
