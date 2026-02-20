# GitHub Configuration

**Project**: Blacklist Intelligence Platform
**Version**: 3.5.64
**Repository**: [qws941/blacklist](https://github.com/qws941/blacklist)

---

## Directory Structure

```
.github/
├── README.md                      # This file
├── ISSUE_TEMPLATE/                # Issue templates
│   ├── bug_report.yml             # Bug report
│   ├── feature_request.yml        # Feature request
│   ├── question.yml               # Question
│   ├── quick-fix.yml              # Quick fix
│   └── config.yml                 # Template config
├── scripts/                       # CI/CD scripts
│   └── validate-services.sh       # Service health validation
└── workflows/                     # GitHub Actions workflows
    ├── README.md                  # Workflow documentation
    ├── ci.yml                     # CI pipeline (push/PR)
    ├── release.yml                # Release pipeline (tag v*)
    ├── build-images.yml           # Reusable: Docker builds
```

---

## Workflows

### 1. CI Pipeline (`ci.yml`)

**Trigger**: Push/PR to `master`

**Jobs**:
1. `detect-changes` — Path-based change detection
2. `lint-backend` / `lint-frontend` — Ruff + ESLint/tsc (parallel)
3. `test-backend` / `test-frontend` — pytest + vitest (parallel)
4. `build-images` — Matrix build (5 services)
5. `e2e` — Playwright tests (smoke/chromium)
6. `push-images` — Push to GHCR (master only)

### 2. Release Pipeline (`release.yml`)

**Trigger**: Tag push `v*`

**Jobs**:
1. `validate` — Check VERSION file matches tag
2. `build-images` — Matrix build (5 Docker images)
3. `package` — Create release tarball bundle
4. `create-release` — GitHub Release with assets
5. `push-to-registry` — Push all images to GHCR
6. `trigger-sandbox` — Watchtower HTTP trigger for auto-deploy
7. `notify` — Slack notification

### 3. Build Images (`build-images.yml`) — Reusable

Matrix Docker build for: `postgres`, `redis`, `collector`, `app`, `frontend`

---

## Issue Templates

| Template | Purpose |
|----------|--------|
| Bug Report | Reproduction steps, expected/actual behavior |
| Feature Request | Description, use case, priority |
| Question | Context and related docs |
| Quick Fix | Urgent fix request with impact scope |

---

## Required Secrets

| Secret | Used By | Description |
|--------|---------|-------------|
| `GITHUB_TOKEN` | All workflows | Auto-provided by GitHub |
| `REGTECH_ID` | release.yml | REGTECH portal ID |
| `REGTECH_PW` | release.yml | REGTECH portal password |
| `POSTGRES_PASSWORD` | release.yml | PostgreSQL password |
| `SLACK_WEBHOOK_URL` | release.yml | Slack notifications (optional) |

---

## Monitoring

**Build Status**: [Actions tab](https://github.com/qws941/blacklist/actions)

| Status | Meaning |
|--------|---------|
| ✅ Success | All jobs passed |
| ❌ Failure | One or more jobs failed |
| ⏳ In Progress | Running |
| ⚠️ Skipped | Skipped due to change detection |

---

## Troubleshooting

**Build failure**:
```bash
docker compose build --no-cache
docker system prune -af
```

**Secrets check**:
```bash
gh secret list
gh secret set SECRET_NAME
```

---

**Last Updated**: 2026-02-15
