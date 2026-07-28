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
jobs:
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
    permissions:
      contents: write
  push-to-registry:
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
""",
        ".github/docker-compose.ci.yml": """
ports:
      - \"3443:443\"
ADMIN_USERNAME: admin
ADMIN_PASSWORD: blacklist-dev-password
""",
        "frontend/Dockerfile": """
FROM node:24-alpine AS builder
FROM node:24-alpine AS runner
""",
        ".github/workflows/_ci-node.yml": 'default: "24"',
        ".gitignore": """
docs/*
!docs/manual/
docs/manual/*
!docs/manual/blacklist-*-release-notes.md
""",
    }


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
            "  notify:\n    permissions: {}",
            "release workflow job 'notify' lacks explicit least-privilege permissions",
        ),
        (
            ".github/workflows/release.yml",
            "      contents: read\n      packages: write",
            "release workflow job 'build-images' lacks explicit least-privilege permissions",
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
    ),
)
def test_validator_rejects_missing_release_contract(
    tmp_path: Path,
    path: str,
    required_text: str,
    message: str,
) -> None:
    files = valid_contract_files()
    files[path] = files[path].replace(required_text, "")
    for relative_path, content in files.items():
        fixture_path = tmp_path / relative_path
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        _ = fixture_path.write_text(content, encoding="utf-8")

    validator_path = tmp_path / ".github" / "scripts" / VALIDATOR_PATH.name
    validator_path.parent.mkdir(parents=True, exist_ok=True)
    _ = validator_path.write_text(VALIDATOR_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(validator_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert message in result.stderr
