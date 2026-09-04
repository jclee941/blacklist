# Deploy Directory Guide

## Overview

Compose inheritance for offline/air-gapped deployment. `base.yml` is the source of truth for all five services (postgres, redis, collector, app, frontend); `docker-compose.yml` and `docker-compose.release.yml` extend it for dev and prod.

## Files

- `base.yml` (293 lines) - shared service definitions, internal TLS everywhere, source of truth.
- `docker-compose.yml` (97 lines) - dev overlay: extends base, adds build contexts, WARP proxy on by default.
- `docker-compose.release.yml` (49 lines) - prod overlay: extends base, uses pre-built GHCR images, WARP forced off.
- `install.sh` (1363 lines) - offline installer: bundle/image integrity checks, Docker install, TLS provisioning, secrets, PostgreSQL bootstrap, health checks.
- `init-secrets.sh` - generates `CREDENTIAL_MASTER_KEY`/`SECRET_KEY`/`CREDENTIAL_ENCRYPTION_KEY` once on first boot and persists them to a shared volume for reuse.
- `.env.example` (104 lines) - required secrets template.
- `redis/Dockerfile` - builds the TLS-only Redis image (see Redis below).
- `prereqs/docker.service` - systemd unit for offline Docker installs.

## Network And TLS

Only `blacklist-frontend` publishes a host port (`443` -> container `3000`). Postgres, Redis, the collector, and the app publish nothing; every service talks over the `blacklist-net` bridge using certificates under `BLACKLIST_TLS_DIR` (default `/etc/blacklist/tls`).

- Frontend: `FRONTEND_TLS_MODE=provided` requires an operator certificate/key at `FRONTEND_TLS_DIR` matching `FRONTEND_TLS_SERVER_NAME`; `install.sh` checks expiry, hostname match, and that the key matches the cert. `self-signed` mode is loopback-only and for development.
- Internal traffic (Postgres, Redis, collector, app): install-generated CA. Postgres uses `sslmode=verify-full`; Redis is TLS-only (`tls-auth-clients no`, plaintext port disabled).

## WARP

Development-only. `docker-compose.yml` defaults `WARP_ENABLED=true` against a host proxy at `host.docker.internal:40000`. `base.yml`, `docker-compose.release.yml`, and `install.sh` force `WARP_ENABLED=false` for release and the installed bundle.

## Install Flow (`install.sh`)

1. Verify the detached manifest signature, `MANIFEST.sha256`, and image `checksums.sha256` before mutation.
2. Install Docker/Compose if missing.
3. Load images and provision internal + frontend TLS material.
4. Start `blacklist-postgres` alone, wait for its health check, then run `configure-runtime-roles.sh` inside the container to bootstrap DB roles.
5. Start the remaining services and wait for every container to report healthy.

## Conventions

- All services attach to the `blacklist-net` bridge and address peers by Compose service name.
- Health checks are mandatory on every service.
- Redis requires `REDIS_PASSWORD`, shared by its own health check plus the app and collector environments.
- `make build` requires a clean working tree; `VERSION` and tag consistency are enforced by the release pipeline.

## Known Issues

- Collector API base URL must be set via `BLACKLIST_API_URL`; the legacy `BACKEND_API_URL` is not read.
- `ADMIN_USERNAME`/`ADMIN_PASSWORD` must be set explicitly before production deployment; there is no fallback login.
