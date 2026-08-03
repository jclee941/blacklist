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
      packages: write
context: ./deploy/redis
API_URL: https://localhost:3443
BASE_URL: https://localhost:3443
E2E_USERNAME: admin
E2E_PASSWORD: blacklist-dev-password
BLACKLIST_TLS_DIR=$RUNNER_TEMP/blacklist-ci-tls
docker compose --env-file "$CI_ENV_FILE" -f deploy/base.yml -f .github/docker-compose.ci.yml up
jobs:
  scan-images:
    steps:
      - with:
          skip-files: usr/local/lib/python3.11/site-packages/pip/_vendor/bom.cdx.json
  e2e:
    timeout-minutes: 60
  ci-gate:
    steps:
      - run: |
          if [ "$result" = "failure" ] || [ "$result" = "cancelled" ]; then
""",
        ".github/workflows/build-images.yml": """
      contents: read
      packages: write
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
      packages: write
  package:
    permissions:
      contents: read
  create-release:
    if: ${{ github.event_name == 'push' && startsWith(github.ref, 'refs/tags/') && !inputs.dry_run }}
    permissions:
      contents: write
  push-to-registry:
    if: ${{ github.event_name == 'push' && startsWith(github.ref, 'refs/tags/') && !inputs.dry_run }}
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
git add \"$VERSION_FILE\" \"$CHANGELOG_FILE\" \"$FRONTEND_PKG\" \"$RELEASE_NOTES_FILE\"
current) NEW_VERSION=\"$CURRENT_VERSION\" ;;
auto) NEW_VERSION=\"$CURRENT_VERSION\" ;;
if [[ \"$BUMP_TYPE\" != \"current\" && \"$BUMP_TYPE\" != \"auto\" ]]; then
CI_WORKFLOW=\"CI\"
gh run list --workflow \"$CI_WORKFLOW\" --commit \"$HEAD_SHA\"
docker compose exec -T blacklist-app test -d /app/tests
""",
        ".github/docker-compose.ci.yml": """
services:
  blacklist-postgres:
    image: blacklist-postgres:ci
  blacklist-redis:
    image: blacklist-redis:ci
ports: !override
      - \"3443:3000\"
ADMIN_USERNAME: admin
ADMIN_PASSWORD: blacklist-dev-password
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
            'git add "$VERSION_FILE" "$CHANGELOG_FILE" "$FRONTEND_PKG" "$RELEASE_NOTES_FILE"',
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
            "      contents: read\n      packages: write",
            "release workflow job 'build-images' lacks explicit least-privilege permissions",
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
            "docker compose exec -T blacklist-app test -d /app/tests",
            "release script treats production images without tests as failed test runs",
        ),
        (
            ".github/workflows/release.yml",
            "    if: ${{ github.event_name == 'push' && startsWith(github.ref, 'refs/tags/') && !inputs.dry_run }}",
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
            "E2E_USERNAME: admin",
            "CI does not provide the E2E username",
        ),
        (
            ".github/workflows/ci.yml",
            "E2E_PASSWORD: blacklist-dev-password",
            "CI does not provide the E2E password",
        ),
        (
            ".github/workflows/ci.yml",
            "skip-files: usr/local/lib/python3.11/site-packages/pip/_vendor/bom.cdx.json",
            "CI Trivy scan does not exclude pip's vendored dependency SBOM",
        ),
        (
            ".github/docker-compose.ci.yml",
            "ADMIN_USERNAME: admin",
            "CI app username does not match E2E credentials",
        ),
        (
            ".github/docker-compose.ci.yml",
            "ADMIN_PASSWORD: blacklist-dev-password",
            "CI app password does not match E2E credentials",
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
