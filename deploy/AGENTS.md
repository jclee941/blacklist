# DEPLOYMENT KNOWLEDGE BASE

**Generated:** 2026-02-27 00:00 Asia/Seoul
**Commit:** cd16ec1
**Branch:** master | **Version:** 5.0.0

## OVERVIEW

Deployment layer for offline/air-gapped environments. Compose inheritance pattern.

## FILES

| File                         | LOC | Role                                                                                            |
| ---------------------------- | --- | ----------------------------------------------------------------------------------------------- |
| `base.yml`                   | 226 | shared service definitions (5 services: app, collector, postgres, redis, frontend; internal TLS everywhere)  |
| `docker-compose.yml`         | 61  | dev extends base (adds build contexts)                                                          |
| `docker-compose.release.yml` | 40  | prod extends base (pre-built GHCR images)                                                       |
| `install.sh`                 | 1147 | offline installer: integrity verify, Docker/Compose install, image loading, internal TLS, secrets, health checks |
| `.env.example`               | 113 | required secrets template                                                                       |
| `prereqs/docker.service`     | 43  | systemd service for offline Docker                                                              |

## COMPOSE INHERITANCE

```
base.yml (source of truth)
├── docker-compose.yml (dev: extends base + build contexts)
└── docker-compose.release.yml (prod: extends base + GHCR images)
```

## CONVENTIONS

- All services attach to the `blacklist-net` bridge and address peers by Compose service name.
- `base.yml` and both extending Compose files declare `blacklist-net` at the top level.
- Published-port inventory: only `blacklist-frontend` publishes host port `443` to container port `3000`; PostgreSQL, Redis, collector, and Flask publish no host ports.
- Redis requires `REDIS_PASSWORD`; its health check plus the app and collector environments receive the same secret.
- Internal service traffic is TLS: PostgreSQL `sslmode=verify-full`, Redis/Flask/Collector HTTPS with the install-generated CA (`/etc/blacklist/tls`).
- Installer auto-detects a host WARP proxy reachable from the Docker bridge and enables the collector proxy; otherwise records `WARP_ENABLED=false`.
- `base.yml` passes through `WARP_PROXY_URL` and `REGTECH_RATE_*`/`REGTECH_BLOCK_THRESHOLD` (empty = collector defaults).
- Health checks mandatory on every service.
- `VERSION` + tag consistency enforced by release pipeline.
- `make build` requires clean working tree.

## KNOWN ISSUES
- Collector API base URL must be provided via `BLACKLIST_API_URL` (legacy `BACKEND_API_URL` is unsupported).
- A stored `system_settings.admin_password` row overrides `ADMIN_PASSWORD` env — env-only rotation silently fails until the row is deactivated.

- Collector API base URL must be provided via `BLACKLIST_API_URL` (legacy `BACKEND_API_URL` is unsupported).
- Admin credentials must be set explicitly (`ADMIN_USERNAME`/`ADMIN_PASSWORD`) before production deployment.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `install.sh` | script | `install.sh:1` | high | offline installer: Docker, images, SSL, secrets, rollback (412L) |
| `base.yml` | compose | `base.yml:1` | high | 5 service definitions (source of truth) |
| `docker-compose.yml` | compose | `docker-compose.yml:1` | med | dev extends base + build contexts |
| `docker-compose.release.yml` | compose | `docker-compose.release.yml:1` | med | prod extends base + GHCR images |
