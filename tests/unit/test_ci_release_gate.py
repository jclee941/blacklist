from pathlib import Path


ROOT = Path(__file__).parents[2]
CI = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
RELEASE = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
RELEASE_SCRIPT = (ROOT / "scripts/release.sh").read_text(encoding="utf-8")


def test_ci_uses_the_complete_push_range_and_forces_release_metadata_checks() -> None:
    assert "github.event.before" in CI
    assert 'DIFF_TARGET="HEAD~1"' not in CI
    assert "metadata:" in CI
    assert "needs.detect-changes.outputs.metadata == 'true'" in CI


def test_ci_e2e_supplies_every_required_authentication_secret() -> None:
    for key in ("FLASK_SECRET_KEY", "JWT_SECRET_KEY", "SETTINGS_ENCRYPTION_KEY"):
        assert f"{key}=" in CI


def test_release_tests_and_scans_the_exact_publishable_images() -> None:
    assert "  test-release:" in RELEASE
    assert "  scan-release-images:" in RELEASE
    assert "  e2e-release:" in RELEASE
    assert "name: image-${{ matrix.service }}" in RELEASE


def test_release_publication_requires_one_successful_gate() -> None:
    assert "  release-gate:" in RELEASE
    assert "needs.release-gate.result == 'success'" in RELEASE
    assert "needs: [validate, package, release-gate]" in RELEASE
    assert "needs: [validate, build-images, release-gate]" in RELEASE


def test_release_notes_use_the_versioned_document_without_stub_fallback() -> None:
    assert '--notes-file "${BUNDLE}-release-notes.md"' in RELEASE
    assert "printf 'Release %s" not in RELEASE


def test_release_script_updates_lockfile_and_breaking_changes() -> None:
    assert 'npm version "$NEW_VERSION" --no-git-tag-version --allow-same-version' in RELEASE_SCRIPT
    assert '"$FRONTEND_LOCK"' in RELEASE_SCRIPT
    assert '"## Breaking Changes"' in RELEASE_SCRIPT
