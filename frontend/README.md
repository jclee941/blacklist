# Blacklist Frontend

**Version:** `4.1.0`

The frontend is the Next.js 15 and React 19 dashboard for Blacklist. It uses the App Router, TypeScript, Tailwind CSS v4, React Query, and the shared API client in `lib/api.ts`.

## Layout

| Path                  | Purpose                                 |
| --------------------- | --------------------------------------- |
| `app/`                | Dashboard pages and route-level UI      |
| `components/`         | Shared application and UI components    |
| `lib/api.ts`          | Required boundary for browser API calls |
| `hooks/` and `types/` | Shared hooks and TypeScript types       |
| `__tests__/`          | Vitest tests                            |
| `e2e/`                | Playwright end-to-end tests             |
| `next.config.ts`      | Standalone output and Flask proxy rules |

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

## Flask Integration

`next.config.ts` proxies `/api/:path*` to Flask at `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:2542`. It also proxies health, metrics, static assets, and legacy UI paths. Keep browser requests in `lib/api.ts` so headers, error handling, and backend contracts stay consistent.

## Authentication

The backend exposes JWT token endpoints, and the API client includes auth helpers. Global JWT enforcement is disabled in the current Flask application, so frontend work must not assume every API route requires a bearer token. Don't store credentials or token secrets in tracked frontend configuration.

## Deployment

The Dockerfile builds Next.js standalone output. Local multi-service development and production-like runs are managed from the repository root with `make dev`, `make dev-prod`, and related Compose commands.
