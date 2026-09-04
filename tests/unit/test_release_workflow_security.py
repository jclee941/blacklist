from pathlib import Path


WORKFLOW = (Path(__file__).parents[2] / ".github" / "workflows" / "release.yml").read_text(
    encoding="utf-8"
)


def test_release_notes_are_passed_as_a_file_not_shell_interpolation() -> None:
    assert "--notes-file" in WORKFLOW
    assert "steps.changelog.outputs.notes" not in WORKFLOW
    assert '--notes-file "${BUNDLE}-release-notes.md"' in WORKFLOW


def test_release_context_values_enter_shell_through_environment() -> None:
    assert "RELEASE_TAG: ${{ github.ref_name }}" in WORKFLOW
    assert "RELEASE_VERSION: ${{ needs.validate.outputs.version }}" in WORKFLOW
    assert 'gh release create "$RELEASE_TAG"' in WORKFLOW


def test_release_bundle_contains_a_detached_manifest_signature() -> None:
    assert "RELEASE_GPG_PRIVATE_KEY: ${{ secrets.RELEASE_GPG_PRIVATE_KEY }}" in WORKFLOW
    assert "MANIFEST.sha256.asc" in WORKFLOW
    assert "gpg --batch --import" in WORKFLOW


def test_release_signing_uses_an_ephemeral_gnupg_home() -> None:
    assert "GNUPGHOME: ${{ runner.temp }}/blacklist-release-gnupg" in WORKFLOW
    assert 'install -d -m 700 "$GNUPGHOME"' in WORKFLOW
    assert "trap cleanup_gnupg EXIT" in WORKFLOW


def test_release_signing_keeps_the_passphrase_out_of_process_arguments() -> None:
    assert '--passphrase "$RELEASE_GPG_PASSPHRASE"' not in WORKFLOW
    assert "--passphrase-fd 0" in WORKFLOW


def test_release_signing_pins_the_expected_key_fingerprint() -> None:
    assert "RELEASE_GPG_FINGERPRINT: ${{ vars.RELEASE_GPG_FINGERPRINT }}" in WORKFLOW
    assert '--local-user "$RELEASE_GPG_FINGERPRINT"' in WORKFLOW
    assert "blacklist-release-signing-key-v1.fingerprint" in WORKFLOW
    assert 'RELEASE_GPG_FINGERPRINT" != "$TRACKED_FINGERPRINT' in WORKFLOW


def test_release_signs_and_publishes_the_final_tarball() -> None:
    assert 'sign_file "${BUNDLE}.tar.gz" "${BUNDLE}.tar.gz.asc"' in WORKFLOW
    assert 'blacklist-*.tar.gz.asc' in WORKFLOW
    archive_index = WORKFLOW.index('-czf "${BUNDLE}.tar.gz"')
    signature_index = WORKFLOW.index('sign_file "${BUNDLE}.tar.gz" "${BUNDLE}.tar.gz.asc"')
    assert archive_index < signature_index


def test_release_publishes_verification_material_and_full_notes() -> None:
    assert "blacklist-*-release-public-key.asc" in WORKFLOW
    assert "blacklist-*-release-key.fingerprint" in WORKFLOW
    assert "blacklist-*-release-notes.md" in WORKFLOW
    assert "printf 'Release %s" not in WORKFLOW
