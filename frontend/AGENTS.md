# FRONTEND KNOWLEDGE BASE

**Generated:** 2026-02-11
**Commit:** 6cd4c24 | **Version:** 3.5.53
**Role:** Dashboard UI (Admin Interface)
**Parent:** [../AGENTS.md](../AGENTS.md)

## OVERVIEW

Next.js 15 admin dashboard. **Air-gap compatible** — all API calls go through proxy.
Tailwind CSS v4 + Radix UI component system.

## STRUCTURE

```
app/                    # App Router
├── (auth)/             # Auth-required routes
├── ip-management/      # IP management
│   ├── IPManagementClient.tsx  # Main client (893L)
│   └── components/     # ✅ Extracted sub-components (v3.5.37)
│       ├── IPManagementTable, IPManagementTabs, IPManagementFilters
│       ├── IPManagementFormModal, DeleteConfirmModal
│       └── useIPManagement (hook)
├── collection/         # Collection management
│   ├── components/     # 7 sub-components
│   └── hooks/          # Custom hooks
├── globals.css         # Tailwind v4
└── page.tsx            # Dashboard root
components/{ui/,features/}  # Radix UI-based
lib/api.ts              # ⚠️ REQUIRED: All API calls go through here
types/                  # TypeScript types
next.config.ts          # /api/* → :2542 rewrite
```

## HOW TO: Add New Page

1. Create `app/<feature>/page.tsx` (Server Component) + `*Client.tsx` (Client Component)
2. Add API methods in `lib/api.ts`
3. Define types in `types/`

**Pattern**: `page.tsx` → Server (data fetching), `*Client.tsx` → Client (interaction, hooks)

## CONVENTIONS

| Convention | Description                                        |
| ---------- | -------------------------------------------------- |
| API calls  | Through `lib/api.ts` only (direct fetch forbidden) |
| Components | `page.tsx` = Server, `*Client.tsx` = Client        |
| State      | Zustand (global UI), React Query (server state)    |
| Styling    | Tailwind utility only (custom CSS forbidden)       |
| Build      | `output: 'standalone'` (Docker optimized)          |

## KNOWN ISSUES

| File                     | Issue                                                              |
| ------------------------ | ------------------------------------------------------------------ |
| `next.config.ts:7`       | Hardcoded API URL → use `API_URL` env var                          |
| `IPManagementClient.tsx` | 893L — sub-components extracted, main file still needs refactoring |
| Dashboard + Collection   | Dual polling (30s + 5s simultaneous)                               |

## DEPLOYMENT

Single container: Nginx(proxy) + Next.js(standalone) + supervisord.
SSL: Production Traefik, development `frontend/ssl/` certificates.

## NOTES

- `components/ui/` — Radix UI primitives, do NOT modify directly
- E2E tests: `tests/e2e/` (Playwright) — MUST run for UI changes
- Prettier(100), single quotes, semicolons required
