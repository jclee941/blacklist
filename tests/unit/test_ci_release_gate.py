from pathlib import Path


ROOT = Path(__file__).parents[2]
CI = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
RELEASE = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
BUILD_IMAGES = (ROOT / ".github/workflows/build-images.yml").read_text(encoding="utf-8")
PUBLISH_LATEST = (ROOT / ".github/workflows/publish-latest.yml").read_text(encoding="utf-8")
RELEASE_SCRIPT = (ROOT / "scripts/release.sh").read_text(encoding="utf-8")


def test_ci_uses_the_complete_push_range_and_forces_release_metadata_checks() -> None:
    assert "github.event.before" in CI
    assert 'DIFF_TARGET="HEAD~1"' not in CI
    assert "metadata:" in CI
    assert "needs.detect-changes.outputs.metadata == 'true'" in CI


def test_ci_e2e_supplies_every_required_authentication_secret() -> None:
    for key in ("FLASK_SECRET_KEY", "JWT_SECRET_KEY", "SETTINGS_ENCRYPTION_KEY"):
        assert f"{key}=" in CI


def test_docs_check_is_enforced_by_ci_and_release() -> None:
    assert "  docs-check:" in CI
    assert "make docs-check" in CI
    assert "docs-check," in CI.split("  ci-gate:", 1)[1]
    assert "make docs-check" in RELEASE.split("  test-release:", 1)[1].split("  scan-release-images:", 1)[0]


def test_ci_builds_scans_and_publishes_all_five_exact_images() -> None:
    assert CI.count("service: [frontend, app, collector, postgres, redis]") >= 2
    assert "Build datastore images" not in CI
    assert "from-artifact: false" not in CI
    assert "dockerfile: deploy/redis/Dockerfile" in CI


def test_manual_build_workflow_is_artifact_only() -> None:
    assert "inputs.push" not in BUILD_IMAGES
    assert "packages: write" not in BUILD_IMAGES
    assert "docker/login-action" not in BUILD_IMAGES
    assert "push: false" in BUILD_IMAGES
    assert "actions/upload-artifact" in BUILD_IMAGES


def test_latest_publication_is_isolated_from_pull_request_code() -> None:
    assert "packages: write" not in CI
    assert "secrets: inherit" not in CI
    assert "workflow_run:" in PUBLISH_LATEST
    assert "github.event.workflow_run.conclusion == 'success'" in PUBLISH_LATEST
    assert "run-id: ${{ github.event.workflow_run.id }}" in PUBLISH_LATEST


def test_release_tests_and_scans_the_exact_publishable_images() -> None:
    assert "  test-release:" in RELEASE
    assert "  scan-release-images:" in RELEASE
    assert "  e2e-release:" in RELEASE
    assert "name: image-${{ matrix.service }}" in RELEASE


def test_release_publication_requires_one_successful_gate() -> None:
    assert "  release-gate:" in RELEASE
    assert "needs.release-gate.result == 'success'" in RELEASE
    assert "needs: [validate, sign-package, release-gate]" in RELEASE
    assert "needs: [validate, build-images, release-gate, sign-package]" in RELEASE


def test_release_signing_occurs_only_after_the_gate() -> None:
    assert RELEASE.index("  release-gate:") < RELEASE.index("  sign-package:")
    package_body = RELEASE.split("  package:", 1)[1].split("  release-gate:", 1)[0]
    assert "RELEASE_GPG_PRIVATE_KEY" not in package_body
    assert "environment: production" not in package_body


def test_release_notes_use_the_versioned_document_without_stub_fallback() -> None:
    assert '--notes-file "${BUNDLE}-release-notes.md"' in RELEASE
    assert "printf 'Release %s" not in RELEASE


def test_release_script_updates_lockfile_and_breaking_changes() -> None:
    assert 'npm version "$NEW_VERSION" --no-git-tag-version --allow-same-version' in RELEASE_SCRIPT
    assert '"$FRONTEND_LOCK"' in RELEASE_SCRIPT
    assert '"## Breaking Changes"' in RELEASE_SCRIPT


def test_release_script_requires_successful_remote_exact_head_ci() -> None:
    assert "Timed out waiting for CI on release commit" in RELEASE_SCRIPT
    assert "Falling back to local tests" not in RELEASE_SCRIPT
    assert "Backend tests passed (docker)" not in RELEASE_SCRIPT
    assert "Backend tests passed (local)" not in RELEASE_SCRIPT


def test_release_commit_passes_ci_before_tag_creation() -> None:
    commit_index = RELEASE_SCRIPT.index('git commit -m "chore(release):')
    push_index = RELEASE_SCRIPT.index("git push origin master")
    ci_index = RELEASE_SCRIPT.index('CI passed on release commit')
    tag_index = RELEASE_SCRIPT.index('git tag -a "v${NEW_VERSION}"')

    assert commit_index < push_index < ci_index < tag_index
