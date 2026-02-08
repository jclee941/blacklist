# CLOUDFLARE EDGE API KNOWLEDGE BASE

**Generated:** 2026-02-08
**Commit:** 450d20c | **Version:** 3.5.39
**Role:** Edge API (read-only mirror + Regtech collection)
**Parent:** [../AGENTS.md](../AGENTS.md)

## OVERVIEW

Cloudflare Workers edge API using Hono.js. Provides read-only blacklist/stats endpoints via D1 (SQLite) + KV cache.
Also includes serverless Regtech collection via `@cloudflare/puppeteer` (Browser Rendering).

## STRUCTURE

```
cloudflare/
├── src/
│   ├── index.ts              # Hono app entry, CORS, route mounting
│   ├── routes/
│   │   ├── blacklist.ts      # Blacklist CRUD (read-only from D1)
│   │   ├── collection.ts     # Regtech collection trigger (Puppeteer)
│   │   ├── health.ts         # Health check endpoint
│   │   └── stats.ts          # Dashboard statistics
│   ├── services/
│   │   ├── database.ts       # D1 query helpers
│   │   └── collector.ts      # Puppeteer-based Regtech scraping
│   └── types/
│       └── index.ts          # Env bindings (D1, KV, Browser)
├── migrations/
│   └── 0000_initial.sql      # D1 schema (mirrors PostgreSQL subset)
├── wrangler.toml              # Workers config (D1 binding, KV, Browser)
├── package.json               # Hono + @cloudflare/puppeteer
└── tsconfig.json
```

## WHERE TO LOOK

| Task                   | Location                  | Notes                        |
|------------------------|---------------------------|------------------------------|
| Add endpoint           | `src/routes/`             | Follow Hono route pattern    |
| Modify DB queries      | `src/services/database.ts`| D1 = SQLite syntax           |
| Change schema          | `migrations/`             | D1 migration format          |
| Update types/bindings  | `src/types/index.ts`      | Env interface for Workers    |
| Configure Workers      | `wrangler.toml`           | Bindings, routes, compat     |

## COMMANDS

```bash
cd cloudflare
npx wrangler dev                  # Local development
npx wrangler deploy               # Deploy to Cloudflare
npx wrangler d1 migrations apply  # Apply D1 migrations
```

## CONVENTIONS

- **Read-only mirror**: D1 data is synced FROM main PostgreSQL — never write authoritative data here
- **KV caching**: Use KV for frequently accessed data (stats, counts)
- **Hono patterns**: `app.route('/path', router)` for modular routing
- **D1 SQL**: SQLite syntax (not PostgreSQL) — no `ON CONFLICT DO UPDATE`, use `INSERT OR REPLACE`

## ANTI-PATTERNS

| Forbidden                          | Why                                    |
|------------------------------------|----------------------------------------|
| Write authoritative data to D1     | D1 is read-only mirror of PostgreSQL   |
| Import from `app/` or `collector/` | Completely isolated service            |
| Use node:fs or node APIs           | Workers runtime, not Node.js           |
| Skip CORS headers                  | Edge API serves cross-origin requests  |

## NOTES

- D1 schema is a SUBSET of PostgreSQL — not all tables are mirrored
- `@cloudflare/puppeteer` requires Browser Rendering binding in wrangler.toml
- `.wrangler/` directory contains local D1 state — gitignored
