# K8S MANIFESTS KNOWLEDGE BASE

**Generated:** 2026-02-08  
**Role:** Kubernetes Deployment Manifests  
**Parent:** ../AGENTS.md

## OVERVIEW

Kubernetes YAML manifests for deploying the platform services (app/collector/frontend/postgres/redis).

## WHERE TO LOOK

| If you need to… | Go to… | Notes |
|---|---|---|
| Base namespace/rbac/etc | `01-base.yaml` | Apply first |
| Secrets/config | `02-secrets.yaml` | Handle carefully; avoid committing real secrets |
| Deploy Postgres | `10-postgres.yaml` | Persistent storage + init |
| Deploy Redis | `11-redis.yaml` | Cache |
| Deploy Flask app | `20-app.yaml` | API service |
| Deploy Collector | `21-collector.yaml` | Background ingestion |
| Deploy Frontend | `30-frontend.yaml` | Dashboard |

## CONVENTIONS

- **Apply order**: base → secrets → postgres/redis → app/collector/frontend.
- **No real secrets**: never commit environment-specific secret values; keep placeholders or sealed/managed secrets.
- **Service boundaries**: app/collector remain shared-nothing except DB/Redis.

## ANTI-PATTERNS

- Editing manifests without understanding the air-gap packaging/deploy flow.
- Introducing cross-service coupling (shared volumes/code sharing) beyond DB/Redis.
