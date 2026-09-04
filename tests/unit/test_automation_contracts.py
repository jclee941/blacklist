# noqa: SIZE_OK - synthetic repository fixtures and contract case tables are kept together
import subprocess
import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).parents[2]
VALIDATOR_PATH = ROOT_DIR / ".github" / "scripts" / "validate_automation_contracts.py"


def valid_contract_files() -> dict[str, str]:
    return {
        ".github/workflows/ci.yml": """
collector/|tests/unit/collector/
node-version: \"24\"
node-version: 24
      contents: read
dockerfile: deploy/redis/Dockerfile
API_URL: https://localhost:3443
BASE_URL: https://localhost:3443
E2E_USERNAME: ${{ env.E2E_USERNAME }}
E2E_PASSWORD: ${{ env.E2E_PASSWORD }}
BLACKLIST_TLS_DIR=$RUNNER_TEMP/blacklist-ci-tls
docker compose --env-file "$CI_ENV_FILE" -f deploy/base.yml -f .github/docker-compose.ci.yml up
jobs:
  scan-images:
    steps:
      - with:
          skip-files: ${{ matrix.service == 'postgres' && 'usr/local/bin/gosu' || '' }}
  docs-check:
    steps:
      - run: make docs-check
  e2e:
    timeout-minutes: 60
  ci-gate:
    needs: [docs-check,]
    steps:
      - run: |
          if [ "$result" = "failure" ] || [ "$result" = "cancelled" ]; then
""",
        ".github/workflows/build-images.yml": """
      contents: read
push: false
""",
        ".github/workflows/publish-latest.yml": """
workflow_run:
      packages: write
github.event.workflow_run.conclusion == 'success'
run-id: ${{ github.event.workflow_run.id }}
""",
        ".github/workflows/security.yml": """
pull_request:
jobs:
  dependency-scan:
    runs-on: ubuntu-latest
""",
        ".github/workflows/release.yml": """
Release notes file not found
if [[ ! -s \"$RELEASE_NOTES_FILE\" ]]; then
scripts/build_offline_bundle.py
actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
jobs:
  validate:
    permissions:
      contents: read
  build-images:
    permissions:
      contents: read
  test-release:
    steps:
      - run: make docs-check
  package:
    permissions:
      contents: read
  release-gate:
    permissions: {}
  sign-package:
    permissions:
      contents: read
  create-release:
    if: >-
      github.event_name == 'push' &&
      startsWith(github.ref, 'refs/tags/') &&
      !inputs.dry_run &&
      needs.release-gate.result == 'success'
    permissions:
      contents: write
  push-to-registry:
    if: >-
      github.event_name == 'push' &&
      startsWith(github.ref, 'refs/tags/') &&
      !inputs.dry_run &&
      needs.release-gate.result == 'success'
    permissions:
      packages: write
  notify:
    permissions: {}
""",
        "scripts/release.sh": """
RELEASE_NOTES_FILE=
Release notes file not found
if [[ ! -s \"$RELEASE_NOTES_FILE\" ]]; then
git ls-files --error-unmatch \"$RELEASE_NOTES_FILE\"
git add \"$VERSION_FILE\" \"$CHANGELOG_FILE\" \"$FRONTEND_PKG\" \"$FRONTEND_LOCK\" \"$RELEASE_NOTES_FILE\"
current) NEW_VERSION=\"$CURRENT_VERSION\" ;;
auto) NEW_VERSION=\"$CURRENT_VERSION\" ;;
if [[ \"$BUMP_TYPE\" != \"current\" && \"$BUMP_TYPE\" != \"auto\" ]]; then
CI_WORKFLOW=\"CI\"
gh run list --workflow \"$CI_WORKFLOW\" --commit \"$HEAD_SHA\"
docker compose exec -T blacklist-app test -d /app/tests
No CI run found for release commit
git push origin master
gh run watch "$CI_RUN_ID" --exit-status
git tag -a "v${NEW_VERSION}"
""",
        ".github/docker-compose.ci.yml": """
services:
  blacklist-postgres:
    image: blacklist-postgres:ci
  blacklist-redis:
    image: blacklist-redis:ci
ports: !override
      - \"3443:3000\"
""",
        "frontend/Dockerfile": """
FROM node:24-alpine AS builder
FROM node:24-alpine AS runner
""",
        ".github/workflows/_ci-node.yml": 'default: "24"',
        ".github/dependabot.yml": """
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/frontend"
""",
        "frontend/package.json": "{}",
        "frontend/package-lock.json": "{}",
        "frontend/e2e/helpers/capture-guide-screenshots.mjs": """
const username = process.env.E2E_USERNAME;
const password = process.env.E2E_PASSWORD;
""",
        ".gitignore": """
docs/*
!docs/manual/
docs/manual/*
!docs/manual/blacklist-*-release-notes.md
""",
    }


def run_validator(tmp_path: Path, files: dict[str, str]) -> subprocess.CompletedProcess[str]:
    for relative_path, content in files.items():
        fixture_path = tmp_path / relative_path
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        _ = fixture_path.write_text(content, encoding="utf-8")

    validator_path = tmp_path / ".github" / "scripts" / VALIDATOR_PATH.name
    validator_path.parent.mkdir(parents=True, exist_ok=True)
    _ = validator_path.write_text(VALIDATOR_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    return subprocess.run(
        [sys.executable, str(validator_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def test_validator_accepts_valid_automation_contracts(tmp_path: Path) -> None:
    result = run_validator(tmp_path, valid_contract_files())

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("path", "required_text", "message"),
    (
        (
            ".gitignore",
            "!docs/manual/blacklist-*-release-notes.md",
            "release notes remain ignored by .gitignore",
        ),
        (
            "scripts/release.sh",
            'git ls-files --error-unmatch "$RELEASE_NOTES_FILE"',
            "release script does not require tracked release notes",
        ),
        (
            "scripts/release.sh",
            'git add "$VERSION_FILE" "$CHANGELOG_FILE" "$FRONTEND_PKG" "$FRONTEND_LOCK" "$RELEASE_NOTES_FILE"',
            "release script does not stage release notes",
        ),
        (
            ".github/workflows/release.yml",
            'if [[ ! -s "$RELEASE_NOTES_FILE" ]]; then',
            "release workflow does not reject empty release notes",
        ),
        (
            ".github/workflows/release.yml",
            "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0",
            "release packaging does not use the approved setup-python action",
        ),
        (
            ".github/workflows/release.yml",
            "  notify:\n    permissions: {}",
            "release workflow job 'notify' lacks explicit least-privilege permissions",
        ),
        (
            ".github/workflows/release.yml",
            "  build-images:\n    permissions:\n      contents: read",
            "release workflow job 'build-images' lacks explicit least-privilege permissions",
        ),
        (
            ".github/workflows/release.yml",
            "  sign-package:\n    permissions:\n      contents: read",
            "release workflow job 'sign-package' lacks explicit least-privilege permissions",
        ),
        (
            "scripts/release.sh",
            'CI_WORKFLOW="CI"',
            "release script does not select the primary CI workflow",
        ),
        (
            "scripts/release.sh",
            'gh run list --workflow "$CI_WORKFLOW" --commit "$HEAD_SHA"',
            "release script does not limit remote verification to the primary CI workflow",
        ),
        (
            "scripts/release.sh",
            'current) NEW_VERSION="$CURRENT_VERSION" ;;',
            "release script cannot tag the current VERSION",
        ),
        (
            "scripts/release.sh",
            'if [[ "$BUMP_TYPE" != "current" && "$BUMP_TYPE" != "auto" ]]; then',
            "current-version release does not skip duplicate metadata changes",
        ),
        (
            "scripts/release.sh",
            'auto) NEW_VERSION="$CURRENT_VERSION" ;;',
            "release script does not select the VERSION file automatically",
        ),
        (
            "scripts/release.sh",
            "No CI run found for release commit",
            "release script does not require successful exact-HEAD remote CI",
        ),
        (
            ".github/workflows/release.yml",
            "needs.release-gate.result == 'success'",
            "release workflow publication jobs are not restricted to tag-triggered non-dry runs",
        ),
        (
            ".github/workflows/ci.yml",
            'docker compose --env-file "$CI_ENV_FILE" -f deploy/base.yml -f .github/docker-compose.ci.yml up',
            "CI E2E does not compose deploy/base.yml with the CI override",
        ),
        (
            ".github/workflows/ci.yml",
            "BLACKLIST_TLS_DIR=$RUNNER_TEMP/blacklist-ci-tls",
            "CI E2E stack does not set BLACKLIST_TLS_DIR",
        ),
        (
            ".github/workflows/ci.yml",
            "API_URL: https://localhost:3443",
            "E2E API calls bypass the frontend proxy",
        ),
        (
            ".github/workflows/ci.yml",
            "BASE_URL: https://localhost:3443",
            "E2E browser target bypasses the frontend proxy",
        ),
        (
            ".github/workflows/ci.yml",
            "E2E_USERNAME: ${{ env.E2E_USERNAME }}",
            "CI does not provide the E2E username",
        ),
        (
            ".github/workflows/ci.yml",
            "E2E_PASSWORD: ${{ env.E2E_PASSWORD }}",
            "CI does not provide the E2E password",
        ),
        (
            ".github/workflows/ci.yml",
            "skip-files: ${{ matrix.service == 'postgres' && 'usr/local/bin/gosu' || '' }}",
            "CI Trivy scan does not apply the verified PostgreSQL gosu false-positive exclusion",
        ),
        (
            ".github/workflows/security.yml",
            "runs-on: ubuntu-latest",
            "PR security dependency-scan job is not GitHub-hosted",
        ),
        (
            ".github/workflows/ci.yml",
            "    timeout-minutes: 60",
            "CI E2E timeout is too short for the full browser matrix",
        ),
        (
            ".github/workflows/ci.yml",
            '          if [ "$result" = "failure" ] || [ "$result" = "cancelled" ]; then',
            "CI gate does not fail when a required job is cancelled",
        ),
        (
            ".github/dependabot.yml",
            '    directory: "/frontend"',
            "Dependabot npm directory does not point to /frontend",
        ),
        (
            "frontend/e2e/helpers/capture-guide-screenshots.mjs",
            "const password = process.env.E2E_PASSWORD;",
            "guide screenshot capture does not require the E2E password from the environment",
        ),
        (
            "frontend/e2e/helpers/capture-guide-screenshots.mjs",
            "const username = process.env.E2E_USERNAME;",
            "guide screenshot capture does not require the E2E username from the environment",
        ),
    ),
)
def test_validator_rejects_missing_automation_contract(
    tmp_path: Path,
    path: str,
    required_text: str,
    message: str,
) -> None:
    files = valid_contract_files()
    files[path] = files[path].replace(required_text, "")
    result = run_validator(tmp_path, files)

    assert result.returncode != 0
    assert message in result.stderr


@pytest.mark.parametrize(
    ("deployment_text", "parallel_text"),
    (
        ("  blacklist-postgres:", "  postgres:"),
        ("  blacklist-redis:", "  redis:"),
        ("image: blacklist-postgres:ci", "image: postgres:15"),
        ("image: blacklist-redis:ci", "image: redis:7-alpine"),
    ),
)
def test_validator_rejects_parallel_ci_datastore_definition(
    tmp_path: Path,
    deployment_text: str,
    parallel_text: str,
) -> None:
    files = valid_contract_files()
    files[".github/docker-compose.ci.yml"] = files[".github/docker-compose.ci.yml"].replace(
        deployment_text,
        parallel_text,
    )
    result = run_validator(tmp_path, files)

    assert result.returncode != 0
    assert "CI compose duplicates PostgreSQL or Redis instead of overriding deployment services" in result.stderr


def test_validator_rejects_ci_compose_credential_overrides(tmp_path: Path) -> None:
    files = valid_contract_files()
    files[".github/docker-compose.ci.yml"] += "\nADMIN_USERNAME: fixed\nADMIN_PASSWORD: fixed\n"

    result = run_validator(tmp_path, files)

    assert result.returncode != 0
    assert "CI compose overrides the generated app username" in result.stderr
    assert "CI compose overrides the generated app password" in result.stderr
