# DEPLOYMENT KNOWLEDGE BASE

**Generated:** 2026-02-22 21:55 Asia/Seoul
**Commit:** 6c134bd
**Branch:** master | **Version:** 3.6.3

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

- Collector `BACKEND_API_URL` vs `BLACKLIST_API_URL` naming mismatch (env var ignored).
- Default `ADMIN_USERNAME`/`ADMIN_PASSWORD` = `admin`/`admin` (security risk for production).
