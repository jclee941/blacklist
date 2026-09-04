# Cloudflare Native Migration Plan

> **Blacklist Intelligence Platform** - Docker Compose to Cloudflare Edge Migration

**Version:** 1.0.0  
**Date:** 2026-01-24  
**Status:** Planning Phase

---

## Executive Summary

This document outlines the migration strategy for moving the Blacklist Intelligence Platform from a Docker Compose-based deployment to a fully Cloudflare-native architecture using Workers, Pages, D1, KV, and Queues.

### Current vs Target Architecture

```text
CURRENT (Docker Compose)              TARGET (Cloudflare Native)
========================              ==========================
blacklist-frontend (Next.js 15)  →   Cloudflare Pages + @cloudflare/next-on-pages
blacklist-app (Flask API)        →   Cloudflare Workers + Hono.js
blacklist-postgres (PostgreSQL)  →   Cloudflare D1 (SQLite)
blacklist-redis (Redis)          →   Cloudflare KV
blacklist-collector (APScheduler)→   Cron Triggers + Queues
Traefik (Reverse Proxy)          →   Cloudflare CDN (Built-in)
```

---

## Phase Overview

| Phase | Component          | Risk   | Effort    | Duration |
| ----- | ------------------ | ------ | --------- | -------- |
| **1** | Frontend → Pages   | Low    | 2-3 days  | Week 1   |
| **2** | API → Workers + D1 | High   | 2-3 weeks | Week 2-4 |
| **3** | Collector → Queues | Medium | 1 week    | Week 5   |
| **4** | Testing & Cutover  | Medium | 1 week    | Week 6   |

---

## Phase 1: Frontend Migration (Cloudflare Pages)

### 1.1 Prerequisites

```bash
# Install adapter
cd frontend
npm install @cloudflare/next-on-pages

# Add build script to package.json
# "pages:build": "npx @cloudflare/next-on-pages"
```

### 1.2 Configuration Changes

**next.config.ts:**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    unoptimized: true, // Or use Cloudflare Image Resizing
  },
  experimental: {
    // Required for Pages compatibility
  },
};

export default nextConfig;
```

**wrangler.toml (frontend):**

```toml
name = "blacklist-frontend"
compatibility_date = "2024-01-01"
compatibility_flags = ["nodejs_compat"]
pages_build_output_dir = ".vercel/output/static"

# KV for ISR cache (optional)
[[kv_namespaces]]
binding = "NEXT_CACHE_WORKERS_KV"
id = "<KV_NAMESPACE_ID>"
```

### 1.3 Edge Runtime Requirements

Each route using server features must export edge runtime:

```typescript
// app/api/[...route]/route.ts
export const runtime = "edge";
```

### 1.4 API Rewrites

Update `frontend/lib/api.ts` to call Workers directly:

```typescript
// Current: /api/* → localhost:2542
// Target: Direct Workers URL or same-origin (if on *.pages.dev)

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://api.blacklist.example.com";
```

### 1.5 Deployment

```bash
# Build for Pages
npm run pages:build

# Deploy via Wrangler
npx wrangler pages deploy .vercel/output/static --project-name=blacklist-frontend
```

---

## Phase 2: API Migration (Workers + D1)

### 2.1 Technology Stack Change

| Current           | Target               | Notes                 |
| ----------------- | -------------------- | --------------------- |
| Flask (Python)    | Hono.js (TypeScript) | Full rewrite required |
| psycopg2          | D1 Binding           | SQL syntax changes    |
| Fernet encryption | Web Crypto API       | Algorithm compatible  |
| Flask-CORS        | Hono CORS middleware | Similar API           |

### 2.2 Hono.js Structure

```text
cloudflare/
├── src/
│   ├── index.ts          # Main entry point
│   ├── routes/
│   │   ├── blacklist.ts  # /api/blacklist/*
│   │   ├── collection.ts # /api/collection/*
│   │   ├── fortinet.ts   # /api/fortinet/*
│   │   └── stats.ts      # /api/stats
│   ├── services/
│   │   ├── database.ts   # D1 wrapper
│   │   ├── cache.ts      # KV wrapper
│   │   └── crypto.ts     # Web Crypto wrapper
│   └── types/
│       └── index.ts      # TypeScript interfaces
├── wrangler.toml
├── schema.sql            # D1 schema
└── package.json
```

### 2.3 Example Route Migration

**Flask (Current):**

```python
@bp.route('/api/blacklist/list', methods=['GET'])
def get_blacklist():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 100, type=int)

    db = current_app.extensions['database']
    result = db.query(
        "SELECT * FROM blacklist_ips WHERE is_active = true LIMIT %s OFFSET %s",
        (limit, (page - 1) * limit)
    )
    return jsonify(result)
```

**Hono.js (Target):**

```typescript
import { Hono } from "hono";
import { D1Database } from "@cloudflare/workers-types";

type Bindings = {
  DB: D1Database;
  CACHE: KVNamespace;
};

const app = new Hono<{ Bindings: Bindings }>();

app.get("/api/blacklist/list", async (c) => {
  const page = Number(c.req.query("page") || 1);
  const limit = Number(c.req.query("limit") || 100);
  const offset = (page - 1) * limit;

  const { results } = await c.env.DB.prepare(
    `SELECT * FROM blacklist_ips WHERE is_active = 1 LIMIT ? OFFSET ?`,
  )
    .bind(limit, offset)
    .all();

  return c.json(results);
});

export default app;
```

### 2.4 D1 Schema Conversion

See `cloudflare/schema.sql` for the complete D1-compatible schema.

**Key Conversions:**

| PostgreSQL           | D1 (SQLite)                         | Notes                     |
| -------------------- | ----------------------------------- | ------------------------- |
| `SERIAL PRIMARY KEY` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Auto-increment            |
| `JSONB`              | `TEXT`                              | Store as JSON string      |
| `VARCHAR(n)`         | `TEXT`                              | SQLite ignores length     |
| `DECIMAL(n,m)`       | `REAL`                              | Floating point            |
| `BOOLEAN`            | `INTEGER`                           | 0/1 instead of true/false |
| `NOW()`              | `datetime('now')`                   | Current timestamp         |
| `INTERVAL '30 days'` | `datetime('now', '-30 days')`       | Date arithmetic           |
| `::jsonb` cast       | `json()` function                   | JSON operations           |
| `column ->> 'key'`   | `json_extract(column, '$.key')`     | JSON access               |
| `FILTER (WHERE ...)` | Subquery or CASE WHEN               | Not supported             |
| `json_object_agg()`  | Manual aggregation                  | Application layer         |

### 2.5 D1 Limitations

| Limit             | Value         | Mitigation             |
| ----------------- | ------------- | ---------------------- |
| Database size     | 10 GB         | Archive old data       |
| Row size          | 1 MB          | Compress JSONB fields  |
| Concurrent writes | Single writer | Queue write operations |
| Query timeout     | 30s (paid)    | Paginate large queries |

### 2.6 wrangler.toml (Workers)

```toml
name = "blacklist-api"
main = "src/index.ts"
compatibility_date = "2024-01-01"
compatibility_flags = ["nodejs_compat"]

# D1 Database
[[d1_databases]]
binding = "DB"
database_name = "blacklist-db"
database_id = "<D1_DATABASE_ID>"

# KV for caching
[[kv_namespaces]]
binding = "CACHE"
id = "<KV_NAMESPACE_ID>"

# Environment variables
[vars]
ENVIRONMENT = "production"

# Secrets (set via wrangler secret put)
# CREDENTIAL_MASTER_KEY
# REGTECH_API_KEY
```

---

## Phase 3: Collector Migration (Queues + Cron)

### 3.1 Architecture

```text
Cron Trigger (0 */6 * * *)
    ↓
Producer Worker
    ↓
Queue (blacklist-collection)
    ↓
Consumer Worker
    ↓
D1 (batch insert)
```

### 3.2 Cron Trigger Configuration

```toml
# wrangler.toml
[triggers]
crons = [
  "0 */6 * * *",   # Every 6 hours (REGTECH collection)
  "0 0 * * *",     # Daily (cleanup old data)
]
```

### 3.3 Queue Configuration

```toml
[[queues.producers]]
queue = "blacklist-collection"
binding = "COLLECTION_QUEUE"

[[queues.consumers]]
queue = "blacklist-collection"
max_batch_size = 100
max_batch_timeout = 30
```

### 3.4 Collector Worker

```typescript
export default {
  // Cron trigger handler
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    if (event.cron === "0 */6 * * *") {
      // REGTECH collection
      const items = await fetchREGTECH(env);
      await env.COLLECTION_QUEUE.sendBatch(
        items.map((item) => ({ body: item })),
      );
    }
  },

  // Queue consumer handler
  async queue(batch: MessageBatch<CollectionItem>, env: Env) {
    const items = batch.messages.map((m) => m.body);
    await batchInsertToD1(env.DB, items);

    // Acknowledge all messages
    batch.ackAll();
  },
};
```

### 3.5 Long-Running Tasks (Durable Objects)

For tasks exceeding 30s CPU time, use Durable Objects:

```typescript
export class CollectionCoordinator extends DurableObject {
  async fetch(request: Request) {
    // Can run for up to 30 minutes
    const result = await this.runLongCollection();
    return new Response(JSON.stringify(result));
  }
}
```

---

## Phase 4: Testing & Cutover

### 4.1 Testing Strategy

| Test Type   | Tool       | Coverage               |
| ----------- | ---------- | ---------------------- |
| Unit Tests  | Vitest     | Services, utilities    |
| Integration | Miniflare  | D1, KV, Queues locally |
| E2E         | Playwright | Full user flows        |
| Load        | k6         | API performance        |

### 4.2 Staging Environment

```bash
# Deploy to staging
wrangler publish --env staging

# Run E2E tests against staging
PLAYWRIGHT_BASE_URL=https://staging.blacklist.pages.dev npx playwright test
```

### 4.3 Data Migration

```bash
# 1. Export from PostgreSQL
pg_dump -t blacklist_ips -t collection_credentials ... --data-only > data.sql

# 2. Convert to SQLite format
# (Use migration script to handle syntax differences)

# 3. Import to D1
wrangler d1 execute blacklist-db --file=data-sqlite.sql
```

### 4.4 Cutover Checklist

- [ ] All E2E tests passing on staging
- [ ] Data migration verified
- [ ] DNS records updated (CNAME to \*.pages.dev)
- [ ] Secrets configured in Workers
- [ ] Monitoring dashboards set up
- [ ] Rollback plan documented

---

## Cost Estimation

### Cloudflare Workers Paid Plan ($5/month)

| Resource         | Free     | Paid      | Expected Usage |
| ---------------- | -------- | --------- | -------------- |
| Workers requests | 100K/day | 10M/month | ~500K/month    |
| Workers CPU      | 10ms     | 30s       | <100ms avg     |
| D1 reads         | 5M/day   | 25B/month | ~10M/month     |
| D1 writes        | 100K/day | 50M/month | ~100K/month    |
| D1 storage       | 5 GB     | 10 GB     | ~2 GB          |
| KV reads         | 100K/day | 10M/month | ~1M/month      |
| KV writes        | 1K/day   | 1M/month  | ~10K/month     |
| Queues           | N/A      | 1M/month  | ~50K/month     |

**Estimated Monthly Cost:** $5-15 (depending on traffic)

---

## Risk Assessment

| Risk                  | Probability | Impact | Mitigation                         |
| --------------------- | ----------- | ------ | ---------------------------------- |
| D1 write contention   | Medium      | High   | Queue writes, batch operations     |
| API rewrite bugs      | High        | High   | Comprehensive E2E tests            |
| Edge runtime limits   | Low         | Medium | Monitor CPU time, optimize queries |
| Data migration errors | Medium      | High   | Validate checksums, dry-run        |
| REGTECH API changes   | Low         | Medium | Abstract in service layer          |

---

## Rollback Plan

1. **DNS Rollback:** Point CNAME back to original server (5 min)
2. **Data Sync:** D1 → PostgreSQL sync script (if writes occurred)
3. **Docker Restart:** `docker-compose up -d` on original server

---

## Appendix

### A. File Mapping

| Current File                    | Cloudflare Equivalent                   |
| ------------------------------- | --------------------------------------- |
| `app/core/routes/api/*.py`      | `cloudflare/src/routes/*.ts`            |
| `app/core/services/*.py`        | `cloudflare/src/services/*.ts`          |
| `postgres/initdb/02-schema.sql` | `cloudflare/schema.sql`                 |
| `collector/scheduler.py`        | Cron Triggers in `wrangler.toml`        |
| `frontend/`                     | Same (with `@cloudflare/next-on-pages`) |

### B. API Endpoint Inventory

| Endpoint                  | Method  | Priority | Notes                 |
| ------------------------- | ------- | -------- | --------------------- |
| `/api/stats`              | GET     | P0       | Dashboard main        |
| `/api/blacklist/list`     | GET     | P0       | Core functionality    |
| `/api/blacklist/search`   | GET     | P0       | Search feature        |
| `/api/blacklist/sources`  | GET     | P1       | Source breakdown      |
| `/api/collection/status`  | GET     | P1       | Collection monitoring |
| `/api/collection/trigger` | POST    | P1       | Manual trigger        |
| `/api/fortinet/pull-logs` | GET     | P2       | Device logs           |
| `/api/settings/*`         | GET/PUT | P2       | Configuration         |
| `/health`                 | GET     | P0       | Health check          |

### C. Environment Variables

| Variable                | Description    | Storage            |
| ----------------------- | -------------- | ------------------ |
| `CREDENTIAL_MASTER_KEY` | Encryption key | wrangler secret    |
| `REGTECH_USERNAME`      | REGTECH auth   | wrangler secret    |
| `REGTECH_PASSWORD`      | REGTECH auth   | wrangler secret    |
| `ENVIRONMENT`           | prod/staging   | wrangler.toml vars |

---

## Next Steps

1. [ ] Review and approve migration plan
2. [ ] Create `cloudflare/` directory structure
3. [ ] Convert PostgreSQL schema to D1 (`cloudflare/schema.sql`)
4. [ ] Set up Cloudflare Pages project
5. [ ] Deploy frontend PoC to Pages
6. [ ] Begin Hono.js API rewrite

---

_Document maintained by: Blacklist Platform Team_
_Last updated: 2026-01-24_
