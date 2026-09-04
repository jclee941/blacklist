# FRONTEND E2E KNOWLEDGE BASE

## OVERVIEW

Playwright E2E suite. 27 `.spec.ts` files total: 26 execute, and `regression/_template-issue-XXX.spec.ts` is excluded from discovery by `testIgnore`.

## STRUCTURE

```text
e2e/
├── *.spec.ts                  # 24 feature specs: dashboard, ip-management, collection(+features/errors/history/management), fortinet, cloudflare, settings, analytics, database, accessibility, performance, navigation, views, error-handling, visual-regression, monitoring, batch-operations, homepage, smoke, auth
├── regression/
│   ├── issue-001-example-navigation.spec.ts
│   ├── issue-002-collection-ip-count-zero.spec.ts
│   ├── _template-issue-XXX.spec.ts   # copy for new regressions, ignored by testIgnore
│   └── README.md
├── helpers/
│   └── capture-guide-screenshots.mjs
├── auth.fixtures.ts           # E2E credential/token helpers
├── collection-process.fixtures.ts
└── global-setup.ts            # logs in once, stores the shared token
```

## AUTHENTICATION

- `global-setup.ts` runs once before the suite: it POSTs `E2E_USERNAME`/`E2E_PASSWORD` to `/api/auth/login` and stores the returned token in `process.env.E2E_AUTH_TOKEN`.
- `auth.fixtures.ts` exposes `getSharedAuthToken()`, `loginViaApi()`, and `authenticatedGet/Post()` so specs reuse that one global token instead of logging in per test.
- `auth.spec.ts` runs serially (`mode: 'serial'`, no retries) and covers login-failure cases plus token-based access.

## PROJECTS (`playwright.config.ts`)

| Project    | Scope                                 | Notes                                                        |
| ---------- | ------------------------------------- | ------------------------------------------------------------ |
| `smoke`    | `smoke.spec.ts` only                  | fast deploy check, zero retries                              |
| `chromium` | everything except smoke/template/auth | default browser, `fullyParallel: true`                       |
| `auth`     | `auth.spec.ts` only                   | depends on `smoke` and `chromium` (plus `webkit` if enabled) |
| `webkit`   | same scope as chromium                | optional, only added when `WEBKIT_ENABLED=true`              |

## CONVENTIONS

- `testDir: './e2e'`, pattern `*.spec.ts`; timeout 60s, assertion timeout 10s.
- New regression tests: copy `regression/_template-issue-XXX.spec.ts` and rename it with the real issue number.
- `BASE_URL` env picks the target; when unset, Playwright boots `npm run dev` itself at `http://localhost:2543`.

## ANTI-PATTERNS

- Logging in per test instead of reusing `getSharedAuthToken()`.
- Adding specs matching `_template-*.spec.ts` directly; they're excluded from every run.
