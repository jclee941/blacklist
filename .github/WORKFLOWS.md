# GitHub Automation Guide

**Repository:** [jclee941/blacklist](https://github.com/jclee941/blacklist)
**Current version:** `4.1.0`

GitHub Actions for this application live in `.github/workflows/`. They are repository-local automation, not reusable workflows for other repositories.

## Canonical Workflows

| Workflow | Trigger | Current purpose |
| --- | --- | --- |
| `ci.yml` | Push and pull request to `master` | Changed-area linting, tests, builds, image scans, E2E, CI gate, and `latest` image publishing from `master` |
| `release.yml` | `v*` tag or manual dispatch | Version and changelog validation, five-image build, release bundle, GitHub Release, GHCR publishing |
| `build-images.yml` | Reusable call or manual dispatch | Build the frontend, app, collector, PostgreSQL, and Redis images |
| `security.yml` | Push and pull request to `master` | Trivy filesystem dependency scan |
| `_ci-node.yml` | Reusable call | Frontend Node lint and type-check support |

## CI Flow

`ci.yml` determines whether frontend, backend, collector, or infrastructure paths changed. It runs only the relevant jobs, then builds the affected application images. Successful builds run Trivy image scans and Playwright E2E tests, and `ci-gate` summarizes those internal CI results. The repository ruleset requires `jclee-bot / pr-metadata`, `jclee-bot / secret-scan`, and `jclee-bot / actionlint`. Pushes to `master` can publish `latest` GHCR images after successful build, scan, and E2E jobs.

## Release Flow

Start a release from a clean `master` checkout:

```bash
make release TYPE=patch
make release-dry TYPE=minor
```

Before releasing, create, add, and commit `docs/manual/blacklist-<next-version>-release-notes.md`. `scripts/release.sh` checks the branch, working tree, test status, and that the versioned release note is non-empty and tracked before changing metadata. It then updates version metadata, generates a changelog entry, commits the release, creates an annotated tag, and pushes. The tag invokes `release.yml`. That workflow validates `VERSION`, `CHANGELOG.md`, and the versioned release note before building images, packages release artifacts, creates the GitHub Release, and publishes five images to GHCR.

## Workflow Change Rules

- Pin every GitHub Action to a full commit SHA with its version comment.
- Use least-privilege `permissions` and preserve concurrency controls.
- Keep CI and release behavior aligned with both `scripts/release.sh` and the workflow source.
- Don't add secrets or webhook values to tracked workflow files. Use repository secrets or variables.
- Run `uv run .github/scripts/validate_automation_contracts.py`, `actionlint`, and `docker compose -f .github/docker-compose.ci.yml config --quiet` before changing automation.
