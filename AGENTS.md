# Blacklist Project Guide

**Repository:** `jclee941/blacklist`
**Current version:** `5.0.0` in `VERSION`

## Overview

Blacklist is a containerized threat-intelligence application for collecting, managing, and distributing IP blacklist data. It is an application repository, not a shared community-health or file-sync repository.

## Architecture

| Area | Location | Role |
| --- | --- | --- |
| Flask application | `app/` | REST API, blacklist and Fortinet functions, settings, monitoring |
| Collector | `collector/` | Isolated Python ETL service for scheduled and manual source collection |
| Frontend | `frontend/` | Next.js 15 dashboard that proxies browser requests to Flask |
| Data services | `postgres/`, `deploy/redis/` | PostgreSQL persistence and Redis support |
| Deployment | `deploy/` | Docker Compose definitions, release bundle files, installation assets |
| CI and release | `.github/workflows/`, `scripts/release.sh` | GitHub Actions checks, image publishing, and releases |

The normal service ports are Flask `2542`, Next.js `2543`, collector `8545`, PostgreSQL `5432`, and Redis `6379`. Docker Compose is the supported local and packaged runtime.

## Where To Start

| Task | Start here |
| --- | --- |
| Flask startup and route registration | `app/core/app.py`, `app/run_app.py` |
| Configuration and environment variables | `app/core/config.py`, `deploy/` |
| Auth token endpoints | `app/core/routes/api/auth_routes.py`, `app/core/auth/` |
| Collector lifecycle and health API | `collector/run_collector.py`, `collector/health_server.py`, `collector/health_routes.py` |
| Browser API boundary | `frontend/lib/api.ts`, `frontend/next.config.ts` |
| Local commands | `Makefile` |
| Release automation | `scripts/release.sh`, `.github/workflows/release.yml` |

## Authentication

`/api/auth/login`, `/api/auth/me`, and `/api/auth/verify` provide JWT token APIs. Global JWT enforcement protects dashboard and application APIs by default; login, health, metrics, static assets, and explicitly `@public` feeds remain open. `DISABLE_JWT_AUTH=true` is an explicit development escape hatch. Admin credentials resolve from the `system_settings` DB rows first, with `ADMIN_USERNAME`/`ADMIN_PASSWORD` env only as fallback — changing env alone does not rotate a stored admin password. Keep credentials and signing secrets in environment variables or the settings store, never in source or documentation examples.

## Development And Verification

Use `make help` for local commands. Common checks are:

```bash
make dev
make verify-lint
make test
cd frontend && npm run typecheck
```

The primary CI workflow is `.github/workflows/ci.yml`. It detects changed areas, runs relevant lint and test jobs, builds images, runs image scans and browser E2E tests, and publishes `latest` images only from pushes to `master`.

## Release Flow

The supported release entry point is `scripts/release.sh`, exposed as `make release` and `make release-dry`. It requires a clean `master` checkout, verifies the current commit, updates `VERSION`, `CHANGELOG.md`, and `frontend/package.json`, creates an annotated `v<version>` tag, and pushes the branch and tag. Tag pushes invoke `.github/workflows/release.yml`, which validates the version and changelog, builds five images, packages a release bundle, creates a GitHub Release, and publishes GHCR images.

## Change Rules

- Keep Flask, collector, and frontend contracts explicit at their HTTP and database boundaries.
- Keep collector code independent from `app/`. It communicates through services and shared storage, not Python imports.
- Route frontend API calls through `frontend/lib/api.ts`; keep proxy behavior in `frontend/next.config.ts` aligned with Flask routes.
- Keep GitHub Actions pinned to full action SHAs and scope permissions to each job.
- Do not add secrets, real credentials, private hosts, or internal network addresses to tracked files.
- Update `VERSION`, `CHANGELOG.md`, and `frontend/package.json` only through the release flow unless a deliberate version maintenance change requires otherwise.

## Review Rules

- Verify that code changes preserve the Flask, collector, and Next.js boundaries above.
- Require tests appropriate to the changed layer: pytest for Python, Vitest or Playwright for frontend, and a workflow syntax review for Actions changes.
- Treat auth changes as security-sensitive. Confirm whether a change affects token issuance only or global request enforcement.
- Review release changes against both `scripts/release.sh` and `.github/workflows/release.yml`.
- Historical documents under `docs/wiki/` and `docs/deliverables/` are records, not current operational truth. Preserve them unless a task explicitly requests a historical correction.
