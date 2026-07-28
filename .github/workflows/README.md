# Blacklist GitHub Actions Workflows

**Current version:** `4.1.0`

This directory contains the active GitHub Actions workflows for `jclee941/blacklist`.

## Primary Workflows

| File | Trigger | Purpose |
| --- | --- | --- |
| `ci.yml` | Push and pull request to `master` | Path-aware quality checks, image builds, image scans, browser E2E, CI gate, and `latest` GHCR publishing from `master` |
| `release.yml` | Tag matching `v*`, manual dispatch | Validate release metadata, build five images, package assets, create a GitHub Release, and publish GHCR tags |
| `build-images.yml` | Reusable call, manual dispatch | Build or export the frontend, app, collector, PostgreSQL, and Redis images |
| `security.yml` | Push and pull request to `master` | Trivy filesystem dependency scan |
| `_ci-node.yml` | Reusable call | Node lint and type-check job used by CI |

## CI Pipeline

`ci.yml` detects frontend, backend, collector, and infrastructure changes. Relevant lint and test jobs run before the application images are built. Successful builds run Trivy image scans and Playwright E2E tests. `ci-gate` collects the results for branch protection. A successful push to `master` can publish `latest` GHCR image tags.

## Release Pipeline

Use the repository release entry point, not a hand-created version tag:

```bash
make release TYPE=patch
make release-dry TYPE=minor
```

`scripts/release.sh` requires a clean `master` checkout and verified tests. It updates `VERSION`, `CHANGELOG.md`, and `frontend/package.json`, creates an annotated `v<version>` tag, and pushes it. `release.yml` validates the version and changelog, builds images, packages a release bundle, creates the GitHub Release, and publishes versioned and `latest` GHCR images.

## Supporting Automation

The numbered workflow files handle branch-to-PR intake, standard and security reviews, Dependabot updates, and human-authored PR auto-merge. CI and release publication remain consolidated in `ci.yml` and `release.yml`.

## Maintenance Rules

- Pin Actions to full commit SHAs and retain their version comments.
- Scope permissions to the workflow or job that needs them.
- Preserve the CI and release contract shared by `scripts/release.sh`, `ci.yml`, and `release.yml`.
- Store sensitive values in GitHub secrets or repository variables, never in workflow YAML.
