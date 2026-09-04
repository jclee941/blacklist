# Blacklist Project Guide

**Repository:** `jclee941/blacklist`
**Current version:** read the authoritative value from `VERSION`

## Overview

Blacklist is a containerized threat-intelligence application for collecting, managing, and distributing IP blacklist data. It is an application repository, not a shared community-health or file-sync repository.

## Architecture

| Area              | Location                                   | Role                                                                   |
| ----------------- | ------------------------------------------ | ---------------------------------------------------------------------- |
| Flask application | `app/`                                     | REST API, blacklist and Fortinet functions, settings, monitoring       |
| Collector         | `collector/`                               | Isolated Python ETL service for scheduled and manual source collection |
| Frontend          | `frontend/`                                | Next.js 15 dashboard that proxies browser requests to Flask            |
| Data services     | `postgres/`, `deploy/redis/`               | PostgreSQL persistence and Redis support                               |
| Deployment        | `deploy/`                                  | Docker Compose definitions, release bundle files, installation assets  |
| CI and release    | `.github/workflows/`, `scripts/release.sh` | GitHub Actions checks, image publishing, and releases                  |

The normal service ports are Flask `2542`, Next.js `2543`, collector `8545`, PostgreSQL `5432`, and Redis `6379`. Docker Compose is the supported local and packaged runtime.

## Where To Start

| Task                                    | Start here                                                                               |
| --------------------------------------- | ---------------------------------------------------------------------------------------- |
| Flask startup and route registration    | `app/core/app.py`, `app/run_app.py`                                                      |
| Configuration and environment variables | `app/core/config.py`, `deploy/`                                                          |
| Auth token endpoints                    | `app/core/routes/api/auth_routes.py`, `app/core/auth/`                                   |
| Collector lifecycle and health API      | `collector/run_collector.py`, `collector/health_server.py`, `collector/health_routes.py` |
| Browser API boundary                    | `frontend/lib/api.ts`, `frontend/server.js`, `frontend/server-routing.js`                |
| Local commands                          | `Makefile`                                                                               |
| Release automation                      | `scripts/release.sh`, `.github/workflows/release.yml`                                    |

## Code Map

| Symbol                  | Type          | Location                                  | Role                                          |
| ----------------------- | ------------- | ----------------------------------------- | --------------------------------------------- |
| `create_app`            | function      | `app/core/app.py`                         | Flask factory, middleware, DI and routes      |
| `initialize_services`   | function      | `app/core/services/service_factory.py`    | 14-service dependency container               |
| `AuthStateService`      | class         | `app/core/services/auth_state_service.py` | transactional password and session generation |
| `BlacklistService`      | class         | `app/core/services/blacklist_service.py`  | blacklist/whitelist decisions and cache       |
| `CollectorApplication`  | class         | `collector/run_collector.py`              | collector lifecycle and scheduler startup     |
| `CollectionScheduler`   | class         | `collector/scheduler/manager.py`          | scheduled/manual collection admission         |
| `RegtechCollector`      | class         | `collector/core/regtech/collector.py`     | REGTECH ETL orchestration                     |
| `api` / `collectionApi` | Axios clients | `frontend/lib/api.ts`                     | browser HTTP and JWT boundary                 |

## Authentication

`/api/auth/login`, `/api/auth/me`, and `/api/auth/verify` provide JWT token APIs. Global JWT enforcement protects dashboard and application APIs; login, health, metrics, and static assets remain open. Fortinet `@public` feeds skip the admin JWT but still require their feed bearer token and allowed source network. `DISABLE_JWT_AUTH=true` is development/testing-only. `AuthStateService` bootstraps missing admin rows from env, then keeps password hash and session generation in one PostgreSQL transaction. DB errors fail closed and never reactivate an env password. Keep credentials and signing secrets in environment variables, 1Password, or the encrypted settings store, never in tracked files.

## Development And Verification

Use `make help` for local commands. Common checks are:

```bash
make dev
make verify-lint
make test
cd frontend && npm run typecheck
cd frontend && npm run test:e2e
```

The primary CI workflow is `.github/workflows/ci.yml`. It runs PR work on GitHub-hosted runners with read-only tokens, builds exactly five image artifacts, and reuses them for Trivy and E2E. A successful `master` CI run triggers `publish-latest.yml`, which publishes those exact artifacts. Workflow details belong in `.github/AGENTS.md`.

## Release Flow

The supported release entry point is `scripts/release.sh`, exposed as `make release` and `make release-dry`; patch is the default bump. It requires clean `master` and successful exact-HEAD CI, updates `VERSION`, `CHANGELOG.md`, `frontend/package.json`, and `frontend/package-lock.json`, then creates and pushes an annotated `v<version>` tag. Tag pushes invoke `.github/workflows/release.yml`: build/test/scan/E2E/package → release gate → production signing → GitHub Release and GHCR publication.

## Change Rules

- Keep Flask, collector, and frontend contracts explicit at their HTTP and database boundaries.
- Keep collector code independent from `app/`. It communicates through services and shared storage, not Python imports.
- Route frontend API calls through `frontend/lib/api.ts`; keep production proxy behavior in `frontend/server.js`/`server-routing.js` aligned with Flask routes.
- Keep GitHub Actions pinned to full action SHAs and scope permissions to each job.
- Do not add secrets, real credentials, private hosts, or internal network addresses to tracked files.
- Update `VERSION`, `CHANGELOG.md`, `frontend/package.json`, and `frontend/package-lock.json` only through the release flow unless a deliberate version maintenance change requires otherwise.
- Keep DDL and grants in `postgres/` migrations/bootstrap scripts; app and collector runtime roles do not own schema objects.
- WARP is development-only. Production base, release overlay, and installer keep it disabled.

## Anti-Patterns

- PR workflows with `packages: write`, inherited secrets, or persistent self-hosted runners.
- Registry publication from a build job instead of gated workflow artifacts.
- Collector access to `collection_credentials`; use `collector_regtech_credentials` only.
- Runtime schema repair endpoints or fallback credential files.

## Review Rules

- Verify that code changes preserve the Flask, collector, and Next.js boundaries above.
- Require tests appropriate to the changed layer: pytest for Python, Vitest or Playwright for frontend, and a workflow syntax review for Actions changes.
- Treat auth changes as security-sensitive. Confirm whether a change affects token issuance only or global request enforcement.
- Review release changes against both `scripts/release.sh` and `.github/workflows/release.yml`.
- Historical documents under `docs/wiki/` and `docs/deliverables/` are records, not current operational truth. Preserve them unless a task explicitly requests a historical correction.
