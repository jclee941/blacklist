from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).parents[2]
VERSION_FILE = REPO_ROOT / "VERSION"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
FRONTEND_PACKAGE = REPO_ROOT / "frontend" / "package.json"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def declared_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def test_version_is_semver() -> None:
    assert SEMVER.match(declared_version())


def test_frontend_package_tracks_the_version() -> None:
    # Given: the bundle builder derives the image tag from VERSION, while the
    # dashboard reports package.json.
    package = json.loads(FRONTEND_PACKAGE.read_text(encoding="utf-8"))
    # Then: a drift between them ships a build that misreports its own version.
    assert package["version"] == declared_version()


def test_changelog_documents_the_current_version() -> None:
    # Given: operators upgrading an air-gapped site read CHANGELOG to learn what
    # breaks. A released version with no entry leaves them blind.
    body = CHANGELOG.read_text(encoding="utf-8")
    assert f"## [{declared_version()}]" in body


def test_breaking_deployment_changes_are_flagged() -> None:
    # Given: this release changes the network model, relocates the environment
    # file, and adds required secrets, so an existing installation cannot be
    # upgraded without operator action.
    body = CHANGELOG.read_text(encoding="utf-8")
    section = body.split(f"## [{declared_version()}]", 1)[1].split("## [", 1)[0]
    assert "Breaking" in section, "the breaking-change section is missing"
