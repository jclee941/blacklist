# FRONTEND TESTS KNOWLEDGE BASE

## OVERVIEW

Vitest unit/component suite. 46 files under `__tests__/`, jsdom environment, global `describe`/`it`/`expect`.

## STRUCTURE

```text
__tests__/
├── server-routing.test.js    # tests server-routing.js proxy/static/security helpers
├── next-config.test.ts       # tests next.config.ts rewrite/redirect/header rules
├── lib/
│   ├── api.test.ts           # runner for lib/api.ts; imports the .cases.ts files below
│   ├── api-auth.cases.ts
│   ├── api-endpoints.cases.ts
│   ├── api-interceptors.cases.ts
│   └── api-test-helpers.ts   # shared axios mock factory
├── components/                # ui/, ip-management/, collection/, NavBar, AuthGate
├── clients/                   # *Client.tsx page-client component tests
├── hooks/                     # use-ip-form, useIPManagement, useCollectionManagement
└── pages/                     # one test per app/*/page.tsx
```

## CONFIGURATION

- `vitest.config.ts`: `environment: 'jsdom'`, `setupFiles: ['./vitest.setup.ts']`, include pattern `__tests__/**/*.{test,spec}.{js,ts,jsx,tsx}`, `e2e/` explicitly excluded.
- `vitest.setup.ts`: imports `@testing-library/jest-dom` and runs `cleanup()` after each test.
- Mocking: 36 of the 46 files call `vi.mock(...)`, mostly to stub `lib/api.ts` or Next.js navigation hooks.

## CONVENTIONS

- One test file per component, hook, or page; the name matches the source file.
- `lib/api.test.ts` doesn't own its test cases; it registers cases exported from the sibling `.cases.ts` modules. Don't rename those exports.
- Component tests render through Testing Library rather than shallow rendering.

## ANTI-PATTERNS

- Adding new `lib/api.ts` coverage as a fresh top-level test file instead of extending the existing `.cases.ts` modules.
- Testing `server.js` directly here; only `server-routing.js`'s pure helpers are unit tested. `server.js` needs a running process, so it stays out of scope for Vitest.
