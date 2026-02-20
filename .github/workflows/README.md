# GitHub Actions Workflows

**Version**: 3.5.64

## Workflow Files

| File | Type | Lines | Trigger | Purpose |
|------|------|-------|---------|--------|
| `ci.yml` | Primary | 283 | Push/PR to `master` | Full CI pipeline |
| `release.yml` | Primary | 243 | Tag `v*` | Release + publish |
| `build-images.yml` | Reusable | 103 | Called by others | Docker image builds |

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
Tag v* → validate → build 5 images → package → create-release + push-to-registry → notify
```

**Jobs**:
| Job | Description |
|-----|-------------|
| `validate` | Check VERSION file matches tag, CHANGELOG has entry |
| `build-images` | Matrix build: postgres, redis, collector, app, frontend |
| `package` | Create release tarball bundle (images + compose + install.sh) |
| `create-release` | GitHub Release with release bundle as asset |
| `push-to-registry` | Push all 5 images to GHCR with version + latest tags |
| `notify` | Slack webhook notification |

---

## 3. Build Images (`build-images.yml`) — Reusable

Matrix strategy builds 5 Docker images in parallel with GitHub Actions cache for layer reuse.

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

# Create a release
git tag v3.5.65 && git push origin v3.5.65
```

---

**Last Updated**: 2026-02-15
