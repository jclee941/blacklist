# GitHub Automation Guide

**Repository:** [jclee941/blacklist](https://github.com/jclee941/blacklist)
GitHub Actions for this application live in `.github/workflows/`. They are repository-local automation, not reusable workflows for other repositories.

## Canonical Workflows

| Workflow             | Trigger                               | Current purpose                                                                                                     |
| -------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `ci.yml`             | Push and pull request to `master`     | Changed-area linting/tests plus one five-image artifact build reused by scans and E2E; `ci-gate` aggregates results |
| `publish-latest.yml` | Successful `master` CI `workflow_run` | Downloads the exact triggering CI artifacts and publishes `latest`; never rebuilds                                  |
| `release.yml`        | `v*` tag or manual dispatch           | Version and changelog validation, five-image build, release bundle, GitHub Release, GHCR publishing                 |
| `build-images.yml`   | Reusable call or manual dispatch      | Build the frontend, app, collector, PostgreSQL, and Redis images                                                    |
| `security.yml`       | Push and pull request to `master`     | Trivy filesystem dependency scan                                                                                    |
| `_ci-node.yml`       | Reusable call                         | Frontend Node lint and type-check support                                                                           |

## CI Flow

`ci.yml` determines changed areas and runs relevant lint/tests. When an image build is needed it builds all five artifacts once; Trivy and Playwright reuse them, and `ci-gate` summarizes the complete run. Branch protection requires `jclee-bot / secret-scan`, `jclee-bot / actionlint`, and `ci-gate`. A successful `master` run triggers `publish-latest.yml`, which downloads those exact artifacts and publishes `latest` without rebuilding.

## Release Flow

Start a release from a clean `master` checkout:

```bash
make release TYPE=patch
make release-dry TYPE=minor
```

Before releasing, create, add, and commit `docs/manual/blacklist-<next-version>-release-notes.md`. `scripts/release.sh` validates the branch, clean worktree, and tracked release note; updates version metadata and changelog; commits and pushes that release candidate to `master`; waits for successful CI on the new commit; then creates and pushes the annotated tag. A failed candidate CI leaves no tag. The tag invokes `release.yml`, which runs its own build/test/scan/E2E/package gate before signing and publication.

The protected `production` environment must provide `RELEASE_GPG_PRIVATE_KEY`, optional `RELEASE_GPG_PASSPHRASE`, and the matching uppercase 40-character `RELEASE_GPG_FINGERPRINT` variable. After test, scan, E2E, unsigned-package, and release gates pass, `sign-package` imports the private key into an ephemeral runner-local GnuPG home, verifies the fingerprint, signs both `MANIFEST.sha256` and the final tarball, and removes the GnuPG home before the job exits.

Pull-request workflows use GitHub-hosted runners with read-only tokens and no inherited repository secrets. Successful `master` CI publishes `latest` images through `publish-latest.yml`, which runs from the default branch and downloads the exact triggering-run artifacts. The `production` environment accepts only `v*` tags, the active `Release Tags` ruleset restricts tag creation and mutation to administrators, and signing runs only after test, E2E, image-scan, and package gates succeed.

## Workflow Change Rules

- Pin every GitHub Action to a full commit SHA with its version comment.
- Use least-privilege `permissions` and preserve concurrency controls.
- Keep CI and release behavior aligned with both `scripts/release.sh` and the workflow source.
- Don't add secrets or webhook values to tracked workflow files. Use repository secrets or variables.
- Run `python3 .github/scripts/validate_automation_contracts.py`, `make docs-check`, `actionlint`, and the applicable Compose config render before changing automation.
