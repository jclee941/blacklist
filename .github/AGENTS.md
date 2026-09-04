# GITHUB AUTOMATION KNOWLEDGE BASE

## OVERVIEW

Repository-local GitHub Actions automation: CI, security scanning, image publishing, and the tag-triggered release pipeline. Not reusable workflows for other repositories. Full narrative detail lives in `.github/WORKFLOWS.md`; this file is the structural index — DAG, permissions, and boundaries.

## WORKFLOW DAG

| Workflow | Trigger | `runs-on` | Key jobs (order) |
| --- | --- | --- | --- |
| `ci.yml` | push/PR to `master` | `ubuntu-latest` | `detect-changes` → lint/test (frontend, backend, collector, integration) → `build` (5-image matrix, artifact-only, needs all lint/test) → `scan-images`, `e2e` (need `build`) → `ci-gate`. `validate-automation` and `coverage-report` run independently — `validate-automation` has no `needs` and starts immediately; `coverage-report` needs only the three `test-*` jobs, not `build`. `ci-gate` needs every job above.
| `security.yml` | push/PR to `master` | `ubuntu-latest` | `dependency-scan` (Trivy fs scan, CRITICAL only) |
| `publish-latest.yml` | `workflow_run` on CI `completed` | `ubuntu-latest` | `publish` — gated on `conclusion == success`, `event == push`, `head_branch == master`; downloads the triggering run's artifacts (no rebuild) and pushes `:latest` to GHCR |
| `build-images.yml` | `workflow_call` / manual dispatch | `ubuntu-latest` | `build` — 5-image matrix, `push: false`, artifact upload only; reused by `release.yml` |
| `release.yml` | `v*` tag push / manual dispatch | `ubuntu-latest` | `validate` → `build-images` (call) + `test-release` → `scan-release-images`, `e2e-release`, `package` (unsigned bundle) → `release-gate` → `sign-package` (env `production`) → `create-release` + `push-to-registry` → `notify` |
| `_ci-node.yml` | `workflow_call` | `ubuntu-latest` | Frontend Node lint/typecheck, called by `ci.yml` |

## PERMISSIONS AND TRUST BOUNDARY

- `ci.yml` and `security.yml`: top-level `permissions: contents: read`, no inherited secrets — GitHub-hosted runners only, safe for untrusted PR heads.
- `build-images.yml`: `contents: read`; produces artifacts, never pushes to a registry.
- `publish-latest.yml`: `actions: read`, `contents: read`, `packages: write` — only job in the non-release path that writes to GHCR, and only after CI succeeded on `master`.
- `release.yml` per-job permissions are least-privilege and mostly `contents: read`; `sign-package`, `create-release`, and `push-to-registry` run under the `production` environment, which GitHub restricts to `v*` tags. `release-gate` and `notify` run with `permissions: {}`.
- The `Release Tags` ruleset restricts tag creation/mutation on `v*` to repository administrators — the `production` environment gate and the ruleset are independent controls, both required to reach signing/publish.

## ARTIFACT FLOW (WHY NO REBUILDS)

`ci.yml build` produces exactly five image artifacts (`image-frontend`, `image-app`, `image-collector`, `image-postgres`, `image-redis`), each `docker save | gzip`, 1-day retention. `scan-images` and `e2e` download and reuse those same artifacts inside the same run. `publish-latest.yml` downloads artifacts from the *triggering* CI run by `run-id` (not a fresh checkout or rebuild) and tags them `:latest`. `release.yml` calls `build-images.yml` to build fresh images tagged at the release `VERSION`, then `scan-release-images`, `e2e-release`, and `package` all reuse that one build. Never add a second build job for the same service — download the existing artifact instead.

## RELEASE GATE SEQUENCE

`sign-package` only runs after `release-gate` (which requires `validate`, `test-release`, `scan-release-images`, `e2e-release`, and `package` to all be `success`) and only on a real tag push with `dry_run` false. `create-release` and `push-to-registry` then require both `release-gate` and `sign-package` to be `success`. Signing uses a runner-local ephemeral GPG home (`GNUPGHOME` under `runner.temp`), verifies the imported key fingerprint against `docs/manual/blacklist-release-signing-key-v1.fingerprint`, and removes the GPG home via `trap ... EXIT` regardless of outcome.

## REQUIRED AUTOMATION CHECKS

- `ci.yml` job `validate-automation` runs `python .github/scripts/validate_automation_contracts.py` on every push/PR — keep workflow/script contracts in sync with this validator.
- Live required checks (branch protection on `master`): `jclee-bot / secret-scan`, `jclee-bot / actionlint` (external checks), and `ci-gate` (this repo's own aggregate job) — `pr-metadata` is no longer required. See `.github/WORKFLOWS.md` for narrative detail.
- Run `python3 .github/scripts/validate_automation_contracts.py`, `actionlint`, and the applicable Compose config render locally before changing any workflow.

## ANTI-PATTERNS

- Adding `packages: write` or inherited secrets to a PR-triggered job (`ci.yml`, `security.yml`) — registry writes belong only to `publish-latest.yml` and the `production`-gated `release.yml` jobs.
- Publishing images from a build job instead of consuming the gated, already-scanned artifact.
- Persistent self-hosted runners — every job here targets `ubuntu-latest`.
- Skipping `release-gate` or `sign-package` ordering, or granting `production` environment access to a non-`v*` ref.
- Editing workflow YAML without re-running `actionlint` and `validate_automation_contracts.py`.

## RELATED

- `.github/WORKFLOWS.md` — narrative guide with the full release-flow walkthrough and change checklist.
- `scripts/AGENTS.md` — `scripts/release.sh` internals (version bump, changelog, tag, push) invoked before `release.yml` runs.
- Root `AGENTS.md` — repository-wide architecture and change rules.
