from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


RELEASE_SCRIPT = Path(__file__).parents[2] / "scripts" / "release.sh"
GIT_ENVIRONMENT = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Release Test",
    "GIT_AUTHOR_EMAIL": "release-test@example.invalid",
    "GIT_COMMITTER_NAME": "Release Test",
    "GIT_COMMITTER_EMAIL": "release-test@example.invalid",
}


def git(repository: Path, *arguments: str) -> None:
    _ = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-c", "core.hooksPath=/dev/null", *arguments],
        cwd=repository,
        env=GIT_ENVIRONMENT,
        capture_output=True,
        check=True,
    )


def commit_file(repository: Path, relative_path: str, content: str, message: str) -> None:
    path = repository / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(content, encoding="utf-8")
    git(repository, "add", relative_path)
    git(repository, "commit", "-q", "-m", message)


def test_dry_run_changelog_lists_every_commit_since_the_last_tag(tmp_path: Path) -> None:
    # Given: a tagged repository whose oldest unreleased commit is a security fix.
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init", "-q", "-b", "master")
    git(repository, "remote", "add", "origin", "https://github.com/example/blacklist.git")
    _ = shutil.copy2(RELEASE_SCRIPT, repository / "release.sh")
    git(repository, "add", "release.sh")
    commit_file(repository, "CHANGELOG.md", "# Changelog\n\n---\n\n## [Unreleased]\n\n---\n", "chore: start changelog")
    commit_file(repository, "VERSION", "1.0.0\n", "chore(release): v1.0.0")
    git(repository, "tag", "-a", "v1.0.0", "-m", "v1.0.0")
    commit_file(repository, "app.txt", "patched\n", "fix(security): oldest unreleased change")
    commit_file(repository, "feature.txt", "added\n", "feat(deploy): newer change")
    commit_file(
        repository,
        "docs/manual/blacklist-1.0.1-release-notes.md",
        "# Notes\n\n## Breaking Changes\n\n- None\n",
        "docs(release): add 1.0.1 release notes",
    )

    # When: the release script previews the next patch release.
    result = subprocess.run(
        ["bash", "release.sh", "patch", "true"],
        cwd=repository,
        env=GIT_ENVIRONMENT,
        capture_output=True,
        check=False,
        text=True,
    )

    # Then: every commit since the tag reaches the changelog, including the oldest one.
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "- fix(security): oldest unreleased change" in output, output
    assert "- feat(deploy): newer change" in output, output
    assert "- docs(release): add 1.0.1 release notes" in output, output
