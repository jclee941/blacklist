# FRONTEND APP KNOWLEDGE BASE

## OVERVIEW

Next.js 15 App Router pages: eight route directories plus the root dashboard. Every `page.tsx` in this tree starts with `'use client'`; stateful domains still split a thin client `page.tsx` from a heavier client `*Client.tsx` component wrapped in `Suspense`.

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

| Symbol                       | Type      | Location                                    | Refs | Role                                 |
| ---------------------------- | --------- | ------------------------------------------- | ---- | ------------------------------------ |
| `Dashboard`                  | component | `page.tsx`                                  | high | main dashboard, stat cards + charts  |
| `RootLayout`                 | component | `layout.tsx`                                | high | sidebar nav + metadata               |
| `Providers`                  | component | `providers.tsx`                             | high | React Query provider wrapper         |
| `CollectionManagementClient` | component | `collection/CollectionManagementClient.tsx` | high | credential CRUD + collection trigger |
| `CollectionHistoryClient`    | component | `collection/CollectionHistoryClient.tsx`    | med  | history table + filtering            |
| `IPManagementClient`         | component | `ip-management/IPManagementClient.tsx`      | med  | unified/whitelist/blacklist tabs     |
| `FortinetClient`             | component | `fortinet/FortinetClient.tsx`               | med  | device list + push controls          |

## CONVENTIONS

- `page.tsx` is a client component (`'use client'`) that wraps the heavier `*Client.tsx` component in `Suspense`; it is not a server component.
- Tailwind CSS + shadcn/ui components.
- Korean labels in UI, English in code.

## ANTI-PATTERNS

- Moving a page to server rendering without first replacing its browser state and local-storage dependencies.

## NOTES

- `page.tsx` (dashboard) is a complexity hotspot and a candidate for component extraction.
- `collection/` has the deepest component tree (4 sub-components).
