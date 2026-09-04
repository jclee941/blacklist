# Blacklist Frontend

**Version:** read the repository root [`VERSION`](../VERSION)

The frontend is the Next.js 15 and React 19 dashboard for Blacklist. It uses the App Router, TypeScript, Tailwind CSS v4, React Query, and the shared API client in `lib/api.ts`.

## Layout

| Path             | Purpose                                 |
| ---------------- | --------------------------------------- |
| `app/`           | Dashboard pages and route-level UI      |
| `components/`    | Shared application and UI components    |
| `lib/api.ts`     | Required boundary for browser API calls |
| `types/`         | Shared TypeScript types                 |
| `__tests__/`     | Vitest tests                            |
| `e2e/`           | Playwright end-to-end tests             |
| `next.config.ts` | Standalone output and Flask proxy rules |

## Run Locally

```bash
npm ci
npm run dev
```

The development server listens on `http://localhost:2543` by default.

```bash
npm run lint
npm run typecheck
npm run test
npm run test:e2e
npm run build
```

## E2E Credentials

Playwright requires `E2E_USERNAME` and `E2E_PASSWORD`. Set both before running authenticated tests. Keep real credentials out of tracked files.

```bash
E2E_USERNAME=admin E2E_PASSWORD='<test-password>' npm run test:e2e
```

When `BASE_URL` isn't set, Playwright starts `npm run dev` at `http://localhost:2543`. Set `BASE_URL` to test an already running environment. CI supplies its own test credentials.

## Flask Integration

`next.config.ts` proxies `/api/:path*` to Flask at `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:2542`. It also proxies health, metrics, static assets, and legacy UI paths. Keep browser requests in `lib/api.ts` so headers, error handling, and backend contracts stay consistent.

## Authentication

The backend enforces JWT authentication on dashboard and protected API routes. The application shell verifies the token before rendering protected pages, `/login` remains public, and API 401 responses clear the expired session. Don't store credentials or token secrets in tracked frontend configuration.

## Deployment

The Dockerfile builds Next.js standalone output. Local multi-service development and production-like runs are managed from the repository root with `make dev`, `make dev-prod`, and related Compose commands.
