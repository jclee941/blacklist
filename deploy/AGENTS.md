# DEPLOYMENT KNOWLEDGE BASE

**Generated:** 2026-02-26 00:00 Asia/Seoul
**Commit:** 803209d
**Branch:** master | **Version:** 3.6.4

## OVERVIEW

Deployment layer for offline/air-gapped environments. Compose inheritance pattern.

## FILES

| File                         | LOC | Role                                                                                            |
| ---------------------------- | --- | ----------------------------------------------------------------------------------------------- |
| `base.yml`                   | 148 | shared service definitions (5 services: app, collector, postgres, redis, frontend)              |
| `docker-compose.yml`         | 61  | dev extends base (adds build contexts)                                                          |
| `docker-compose.release.yml` | 40  | prod extends base (pre-built GHCR images)                                                       |
| `install.sh`                 | 412 | offline installer: Docker/Compose install, image loading, SSL, secrets, health checks, rollback |
| `.env.example`               | 113 | required secrets template                                                                       |
| `prereqs/docker.service`     | 43  | systemd service for offline Docker                                                              |

## COMPOSE INHERITANCE

```
base.yml (source of truth)
├── docker-compose.yml (dev: extends base + build contexts)
└── docker-compose.release.yml (prod: extends base + GHCR images)
```

## CONVENTIONS

- `network_mode: host` for all services.
- Health checks mandatory on every service.
- `VERSION` + tag consistency enforced by release pipeline.
- `make build` requires clean working tree.

## KNOWN ISSUES

- Collector API base URL must be provided via `BLACKLIST_API_URL` (legacy `BACKEND_API_URL` is unsupported).
- Admin credentials must be set explicitly (`ADMIN_USERNAME`/`ADMIN_PASSWORD`) before production deployment.


## CODE MAP

| Symbol | Type | Location | Refs | Role |
| --- | --- | --- | --- | --- |
| `install.sh` | script | `install.sh:1` | high | offline installer: Docker, images, SSL, secrets, rollback (412L) |
| `base.yml` | compose | `base.yml:1` | high | 5 service definitions (source of truth) |
| `docker-compose.yml` | compose | `docker-compose.yml:1` | med | dev extends base + build contexts |
| `docker-compose.release.yml` | compose | `docker-compose.release.yml:1` | med | prod extends base + GHCR images |