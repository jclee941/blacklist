# GitHub Actions Workflows

**Version**: 3.6.3

## Workflow Files

| File | Type | Trigger | Purpose |
|------|------|---------|---------|
| `ci.yml` | Primary | Push/PR to `master` | Full CI: detect, lint, test, build, E2E, push |
| `release.yml` | Primary | Tag `v*`, manual dispatch | Validate + package + release + registry publish |
| `build-images.yml` | Reusable/Manual | `workflow_call`, manual dispatch | Build Docker images, optionally push |
| `_ci-node.yml` | Reusable | `workflow_call` | Shared Node lint/typecheck/test pipeline |
| `auto-merge.yml` | Automation | `pull_request_target` | Enable PR auto-merge for trusted criteria |
| `labeler.yml` | Automation | `pull_request_target` | Apply labels based on path rules |
| `security.yml` | Security | Push/PR to `master` | CodeQL SAST + Trivy dependency/image scanning |

## 1. `ci.yml` — CI Pipeline

**Trigger**: Push or PR to `master`

```text
Push/PR
  -> detect-changes
  -> lint-backend + lint-frontend
  -> test-backend + test-collector + test-frontend
  -> test-integration (after test-backend)
  -> build
  -> scan-images + e2e (parallel)
  -> push-images (push on master only)
```

Key points:
- Uses `vars.RUNNER` with fallback to `ubuntu-latest`
- Backend and collector lint jobs share Ruff checks
- Frontend lint/typecheck runs via `_ci-node.yml`
- E2E runs against `.github/docker-compose.ci.yml`
 Image scanning via Trivy (scan-images job) blocks push

## 2. `release.yml` — Release Pipeline

**Trigger**:
- Tag push matching `v*`
- Manual `workflow_dispatch` with `dry_run`

```text
validate -> build-images -> package -> create-release -> push-to-registry -> notify
```

Key points:
 Enforces `VERSION` file match with tag and CHANGELOG entry (hard fail)
- Packages release tarball + checksums
- Creates GitHub Release via `gh release create`
- Pushes `version` and `latest` tags to GHCR
- Optional Slack notification via `vars.SLACK_WEBHOOK_URL`

## 3. `build-images.yml` — Reusable Builder

- Builds matrix: `frontend`, `app`, `collector`, `postgres`, `redis`
- Supports `push: true/false`
- Exports image artifacts when not pushing

## 4. Automation Workflows

 `auto-merge.yml`: enables squash auto-merge for Dependabot, repo owner, or `auto-merge` label
 `labeler.yml`: syncs PR labels using `.github/labeler.yml`

## 5. `security.yml` — Security Scanning

**Trigger**: Push or PR to `master` (event-based, no cron)

 **CodeQL**: SAST analysis for Python and JavaScript
 **Trivy**: Filesystem dependency scan (CRITICAL/HIGH severity)
 Runs in parallel with CI pipeline

## Manual Commands

```bash
# Run CI on master
gh workflow run ci.yml --ref master

# Run release workflow as dry run
gh workflow run release.yml -f dry_run=true

# Trigger release by tag
git tag v3.6.3 && git push origin v3.6.3
```

**Last Updated**: 2026-02-21
