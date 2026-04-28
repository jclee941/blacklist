# GitHub Configuration

**Project**: Blacklist Intelligence Platform  
**Version**: 3.6.9  
**Repository**: [qws941/blacklist](https://github.com/qws941/blacklist)

## Directory Structure

```text
.github/
├── README.md
├── CODEOWNERS
├── dependabot.yml
├── docker-compose.ci.yml
├── labeler.yml
├── scripts/
└── workflows/
    ├── README.md
    ├── _ci-node.yml
    ├── auto-merge.yml
    ├── build-images.yml
    ├── ci.yml
    ├── codex-auto-issue.yml
    ├── labeler.yml
    ├── release.yml
    ├── security.yml
    └── stale.yml
```

## Workflows

### 1) CI (`ci.yml`)

- Trigger: push/PR to `master`
- Purpose: detect-changes -> lint -> unit tests -> image build -> E2E -> GHCR push
- Notes: uses `vars.RUNNER` fallback (`ubuntu-latest`), supports frontend/backend/collector path gating

### 2) Release (`release.yml`)

- Trigger: tag push `v*` and manual `workflow_dispatch` (`dry_run`)
- Purpose: validate VERSION/tag, build images, package tarball, GitHub Release, GHCR publish

### 3) Build Images (`build-images.yml`)

- Trigger: reusable (`workflow_call`) + manual (`workflow_dispatch`)
- Purpose: build/export or push Docker images for `frontend`, `app`, `collector`, `postgres`, `redis`

### 4) Reusable Node CI (`_ci-node.yml`)

- Trigger: `workflow_call`
- Purpose: shared Node job for lint/typecheck/test with configurable working directory

### 5) Auto Merge (`auto-merge.yml`)

- Trigger: `pull_request_target` (opened/synchronize/reopened/labeled)
- Purpose: enable squash auto-merge for Dependabot, repo owner, or PRs labeled `auto-merge`

### 6) Auto Labeler (`labeler.yml`)

- Trigger: `pull_request_target` (opened/synchronize/reopened)
- Purpose: sync labels from `.github/labeler.yml` path rules

### 7) Stale Cleanup (`stale.yml`)

- Trigger: daily cron + manual dispatch
- Purpose: mark/close inactive issues and PRs

### 8) Security (`security.yml`)

- Trigger: push/PR to `master`
- Purpose: CodeQL SAST analysis (Python + JavaScript) + Trivy filesystem dependency scan

### 9) Codex Auto Issue (`codex-auto-issue.yml`)

- Trigger: issue labeled `codex`
- Purpose: post `@codex` comment to trigger Codex bot

## Key Config Files

- `CODEOWNERS`: review ownership rules
- `dependabot.yml`: dependency update policy
- `docker-compose.ci.yml`: E2E compose stack used in CI
- `labeler.yml`: path-to-label mapping for PR auto-labeling

## Required Repository Settings / Secrets

- `vars.RUNNER` (optional): set to `self-hosted` to run all workflows on self-hosted runners
- `GITHUB_TOKEN`: auto-provided by GitHub Actions
- `vars.SLACK_WEBHOOK_URL` (optional): release notification target

## Quick Checks

```bash
# List workflows
gh workflow list

# Manually run CI on master
gh workflow run ci.yml --ref master

# Manually run release workflow (dry run)
gh workflow run release.yml -f dry_run=true
```

**Last Updated**: 2026-02-26
