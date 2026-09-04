# FRONTEND APP KNOWLEDGE BASE

## OVERVIEW

Next.js 15 App Router pages: eight route directories plus the root dashboard. Stateful domains commonly pair a server `page.tsx` with a client `*Client.tsx` component.

## STRUCTURE

```text
app/
├── page.tsx                 # Dashboard, heaviest page
├── layout.tsx               # RootLayout + NavBar
├── providers.tsx            # QueryClient provider
├── error.tsx                # global error boundary
├── not-found.tsx            # 404 page
├── offline.tsx              # offline indicator
├── globals.css              # Tailwind base styles
├── analytics/
│   └── page.tsx             # analytics charts
├── collection/
│   ├── page.tsx             # tab layout: management + history
│   ├── CollectionManagementClient.tsx
│   ├── CollectionHistoryClient.tsx
│   └── components/          # CollectorCard, CollectionStats, CredentialEditModal
├── database/
│   ├── page.tsx             # database overview
│   └── DatabaseOverviewClient.tsx
├── fortinet/
│   ├── page.tsx             # FortiGate management
│   └── FortinetClient.tsx
├── ip-management/
│   ├── page.tsx             # unified IP management
│   ├── IPManagementClient.tsx
│   └── components/          # IPFormFields, IPManagementFormModal, IPManagementTable, IPManagementFilters, IPManagementTabs, DeleteConfirmModal
├── cloudflare/
│   └── page.tsx             # Cloudflare integration
├── login/
│   └── page.tsx             # public login (no JWT)
└── settings/
    ├── page.tsx             # system settings
    └── CloudflareSettings.tsx  # Cloudflare credential panel
```

## CODE MAP

| Symbol                       | Type      | Location                                       | Refs | Role                                 |
| ---------------------------- | --------- | ---------------------------------------------- | ---- | ------------------------------------ |
| `Dashboard`                  | component | `page.tsx:44`                                  | high | main dashboard, stat cards + charts  |
| `RootLayout`                 | component | `layout.tsx:11`                                | high | sidebar nav + metadata               |
| `Providers`                  | component | `providers.tsx:6`                              | high | React Query provider wrapper         |
| `CollectionManagementClient` | component | `collection/CollectionManagementClient.tsx:19` | high | credential CRUD + collection trigger |
| `CollectionHistoryClient`    | component | `collection/CollectionHistoryClient.tsx:51`    | med  | history table + filtering            |
| `IPManagementClient`         | component | `ip-management/IPManagementClient.tsx:12`      | med  | unified/whitelist/blacklist tabs     |
| `FortinetClient`             | component | `fortinet/FortinetClient.tsx:25`               | med  | device list + push controls          |

## CONVENTIONS

- Server page (`page.tsx`) wraps client component (`*Client.tsx`) with Suspense.
- All data fetching through `lib/api.ts`, no direct `fetch()`.
- Tailwind CSS + shadcn/ui components.
- Korean labels in UI, English in code.

## ANTI-PATTERNS

- Direct API calls bypassing `lib/api.ts`.
- Server components with `"use client"` that should stay server-rendered.

## NOTES

- `page.tsx` (dashboard) is a complexity hotspot and a candidate for component extraction.
- `collection/` has the deepest component tree (4 sub-components).
