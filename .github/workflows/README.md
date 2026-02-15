# GitHub Actions Workflows

**Version**: 3.5.64

## Workflow Files

| File | Type | Lines | Trigger | Purpose |
|------|------|-------|---------|--------|
| `ci.yml` | Primary | 283 | Push/PR to `master` | Full CI pipeline |
| `release.yml` | Primary | 243 | Tag `v*` | Release + publish |
| `deploy-sandbox.yml` | Primary | 324 | Manual / release | Sandbox deployment |
| `build-images.yml` | Reusable | 103 | Called by others | Docker image builds |
| `run-tests.yml` | Reusable | 76 | Called by others | Test execution |

---

## 1. `ci.yml` — CI Pipeline

**Trigger**: Push or PR to `master` branch

```
Push/PR → detect-changes → lint (parallel) → test (parallel) → build (matrix) → e2e → push-images
```

**Jobs**:
| Job | Runs On | Depends On | Description |
|-----|---------|------------|-------------|
| `detect-changes` | self-hosted | — | Path filter for backend/frontend/collector changes |
| `lint-backend` | self-hosted | detect-changes | Ruff linter |
| `lint-frontend` | self-hosted | detect-changes | ESLint + tsc --noEmit |
| `test-backend` | self-hosted | lint-backend | pytest (785+ tests) |
| `test-frontend` | self-hosted | lint-frontend | vitest (207+ tests) |
| `build-images` | self-hosted | test-* | Matrix build: 5 Docker images |
| `e2e` | self-hosted | build-images | Playwright smoke + chromium |
| `push-images` | self-hosted | e2e | Push to GHCR (master branch only) |

**Concurrency**: Auto-cancels in-progress runs on new push.

---

## 2. `release.yml` — Release Pipeline

**Trigger**: Tag push matching `v*`

```
Tag v* → validate → build 5 images → package-airgap → create-release + push-to-registry → trigger-sandbox → notify
```

**Jobs**:
| Job | Description |
|-----|-------------|
| `validate` | Check VERSION file matches tag, CHANGELOG has entry |
| `build-images` | Matrix build: postgres, redis, collector, app, frontend |
| `package-airgap` | Create tarball bundle (images + compose + install.sh) |
| `create-release` | GitHub Release with air-gap bundle as asset |
| `push-to-registry` | Push all 5 images to GHCR with version + latest tags |
| `trigger-sandbox` | Watchtower HTTP API call for auto-pull on sandbox |
| `notify` | Slack webhook notification |

---

## 3. `deploy-sandbox.yml` — Sandbox Deploy

**Trigger**: `workflow_dispatch` or called by release pipeline

**Steps**:
1. SSH to sandbox VM (192.168.50.220)
2. Pull latest images from `ghcr.io/qws941/blacklist-*:latest`
3. `docker compose up -d` with GHCR images
4. Health check: `/health` on all services

---

## 4. `build-images.yml` — Reusable Build

Matrix strategy builds 5 Docker images in parallel with GitHub Actions cache for layer reuse.

## 5. `run-tests.yml` — Reusable Tests

Runs backend (pytest) and frontend (vitest) tests. Called by `ci.yml`.

---

## Runner Requirements

All workflows use `self-hosted` runners:

- Docker 24+
- Docker Compose v2
- Node.js 20
- Python 3.11
- Git, SSH access

---

## Manual Triggers

```bash
# Trigger CI manually
gh workflow run ci.yml --ref master

# Trigger sandbox deploy
gh workflow run deploy-sandbox.yml --ref master

# Create a release
git tag v3.5.65 && git push origin v3.5.65
```

---

**Last Updated**: 2026-02-15
