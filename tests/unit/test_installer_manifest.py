from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest


INSTALLER = Path(__file__).parents[2] / "deploy" / "install.sh"
BUNDLE_IMAGES = (
    "blacklist-app.tar.gz",
    "blacklist-collector.tar.gz",
    "blacklist-frontend.tar.gz",
    "blacklist-postgres.tar.gz",
    "blacklist-redis.tar.gz",
)
PREREQ_FILES = (
    "prereqs/docker-29.2.1.tgz",
    "prereqs/docker-compose-linux-x86_64",
    "prereqs/docker.service",
)
MANIFEST_PATHS = (
    "install.sh",
    "docker-compose.yml",
    "bin/ss",
    "etc/blacklist/.env",
    *(f"images/{image_name}" for image_name in BUNDLE_IMAGES),
    "images/checksums.sha256",
    *PREREQ_FILES,
)
FAKE_SS = """#!/bin/sh
exit 0
"""


def prepare_bundle(tmp_path: Path) -> dict[str, str]:
    installer = tmp_path / "install.sh"
    _ = shutil.copy2(INSTALLER, installer)

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    checksum_lines: list[str] = []
    for image_name in BUNDLE_IMAGES:
        payload = f"payload:{image_name}".encode()
        _ = (images_dir / image_name).write_bytes(payload)
        checksum_lines.append(f"{hashlib.sha256(payload).hexdigest()}  {image_name}")
    _ = (images_dir / "checksums.sha256").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )

    _ = (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")

    prereqs_dir = tmp_path / "prereqs"
    prereqs_dir.mkdir()
    _ = (prereqs_dir / "docker-29.2.1.tgz").write_bytes(b"docker-tarball")
    _ = (prereqs_dir / "docker-compose-linux-x86_64").write_bytes(b"compose-binary")
    _ = (prereqs_dir / "docker.service").write_text("[Service]\n", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    ss = bin_dir / "ss"
    _ = ss.write_text(FAKE_SS, encoding="utf-8")
    _ = ss.chmod(0o755)

    env_file = tmp_path / "etc" / "blacklist" / ".env"
    env_file.parent.mkdir(parents=True)
    _ = env_file.write_text("", encoding="utf-8")

    environment = os.environ.copy()
    environment["PATH"] = f"{bin_dir}{os.pathsep}{environment['PATH']}"
    environment["BLACKLIST_ENV_FILE"] = str(env_file)
    return environment


def run_verification(
    tmp_path: Path,
    environment: dict[str, str],
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(tmp_path / "install.sh"),
            "--verify-only",
            "--skip-posture-check",
            *arguments,
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )


def write_manifest(
    tmp_path: Path,
    listed_paths: tuple[str, ...] = MANIFEST_PATHS,
) -> None:
    lines = [
        f"{hashlib.sha256((tmp_path / relative_path).read_bytes()).hexdigest()}  {relative_path}"
        for relative_path in listed_paths
    ]
    _ = (tmp_path / "MANIFEST.sha256").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def test_missing_manifest_is_fatal(tmp_path: Path) -> None:
    # Given: an otherwise complete offline bundle without its root manifest.
    environment = prepare_bundle(tmp_path)

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: the absent manifest blocks installation.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "MANIFEST.sha256" in output, output


def test_tampered_bundle_file_fails_manifest(tmp_path: Path) -> None:
    # Given: a complete manifested bundle whose installer is modified afterwards.
    environment = prepare_bundle(tmp_path)
    write_manifest(tmp_path)
    with (tmp_path / "install.sh").open("a", encoding="utf-8") as installer:
        _ = installer.write("\n# tamper\n")

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: verification refuses the modified installer and names it.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "install.sh" in output, output


def test_tampered_prereq_tarball_is_rejected(tmp_path: Path) -> None:
    # Given: a manifested Docker prerequisite that is modified afterwards.
    environment = prepare_bundle(tmp_path)
    write_manifest(tmp_path)
    docker_tarball = tmp_path / "prereqs" / "docker-29.2.1.tgz"
    with docker_tarball.open("ab") as tarball:
        _ = tarball.write(b"x")

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: verification refuses the tarball and names it.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "prereqs/docker-29.2.1.tgz" in output, output


def test_entry_verification_precedes_extraction() -> None:
    # Given: the installer functions that mutate privileged system paths.
    installer_source = INSTALLER.read_text(encoding="utf-8")
    docker_body = installer_source.split("\ninstall_docker_offline() {", 1)[1].split("\n}", 1)[0]
    compose_body = installer_source.split("\ninstall_docker_compose() {", 1)[1].split("\n}", 1)[0]

    # When: the last verification before each privileged operation is located.
    tar_index = docker_body.rfind('tar -xzf "$docker_tgz"')
    tar_verify_index = docker_body.rfind("verify_manifest_entry", 0, tar_index)
    service_copy_index = docker_body.rfind('cp "${prereqs_dir}/docker.service"')
    service_verify_index = docker_body.rfind("verify_manifest_entry", 0, service_copy_index)
    compose_copy_index = compose_body.rfind('cp "$compose_bin"')
    compose_verify_index = compose_body.rfind("verify_manifest_entry", 0, compose_copy_index)

    # Then: every root extraction or copy has an in-function last-moment verification.
    assert 0 <= tar_verify_index < tar_index, docker_body
    assert tar_index < service_verify_index < service_copy_index, docker_body
    assert 0 <= compose_verify_index < compose_copy_index, compose_body


def test_manifest_entry_missing_from_manifest_is_fatal(tmp_path: Path) -> None:
    # Given: a Docker tarball present on disk but omitted from an otherwise valid manifest.
    environment = prepare_bundle(tmp_path)
    listed_paths = tuple(
        relative_path
        for relative_path in MANIFEST_PATHS
        if relative_path != "prereqs/docker-29.2.1.tgz"
    )
    write_manifest(tmp_path, listed_paths)

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: the unlisted privileged prerequisite is refused by name.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "prereqs/docker-29.2.1.tgz" in output, output


def test_valid_manifest_passes(tmp_path: Path) -> None:
    # Given: an untampered bundle with every fixture payload listed by bare path.
    environment = prepare_bundle(tmp_path)
    write_manifest(tmp_path)

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: the manifest gate runs and accepts the bundle.
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Bundle manifest verified" in output, output


def test_unlisted_compose_override_is_fatal(tmp_path: Path) -> None:
    environment = prepare_bundle(tmp_path)
    write_manifest(tmp_path)
    _ = (tmp_path / "docker-compose.override.yml").write_text(
        "services:\n  blacklist-app:\n    privileged: true\n",
        encoding="utf-8",
    )

    result = run_verification(tmp_path, environment)

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "docker-compose.override.yml" in output


def test_empty_manifest_is_fatal(tmp_path: Path) -> None:
    # Given: an otherwise complete bundle with a zero-entry root manifest.
    environment = prepare_bundle(tmp_path)
    _ = (tmp_path / "MANIFEST.sha256").write_text("\n", encoding="utf-8")

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: verifying zero payloads is fatal.
    assert result.returncode != 0, result.stdout + result.stderr


@pytest.mark.parametrize("listed_name", ["./install.sh", "*install.sh"])
def test_manifest_names_are_normalised(tmp_path: Path, listed_name: str) -> None:
    # Given: a valid manifest using a supported producer spelling for install.sh.
    environment = prepare_bundle(tmp_path)
    write_manifest(tmp_path)
    manifest = tmp_path / "MANIFEST.sha256"
    lines = manifest.read_text(encoding="utf-8").splitlines()
    installer_hash = hashlib.sha256((tmp_path / "install.sh").read_bytes()).hexdigest()
    separator = " " if listed_name.startswith("*") else "  "
    lines[0] = f"{installer_hash}{separator}{listed_name}"
    _ = manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: both path spellings resolve to the same bundle file.
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Bundle manifest verified" in output, output


def test_signature_is_skipped_without_keyring(tmp_path: Path) -> None:
    # Given: a valid unsigned bundle on a host without the provisioned release keyring.
    environment = prepare_bundle(tmp_path)
    write_manifest(tmp_path)

    # When: signature verification is optional.
    result = run_verification(tmp_path, environment)

    # Then: verification succeeds while announcing the skipped authenticity check.
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "signature verification skipped" in output.lower(), output


def test_missing_signature_is_fatal_when_trusted_keyring_exists(tmp_path: Path) -> None:
    # Given: a valid unsigned bundle and an explicitly configured trusted keyring.
    environment = prepare_bundle(tmp_path)
    write_manifest(tmp_path)
    keyring = tmp_path.parent / f"{tmp_path.name}-trusted-release-keyring.gpg"
    _ = keyring.write_bytes(b"trusted-keyring-fixture")
    environment["BLACKLIST_RELEASE_KEYRING"] = str(keyring)

    # When: detached signature verification runs without MANIFEST.sha256.asc.
    result = run_verification(tmp_path, environment)

    # Then: authenticity cannot be silently downgraded to checksum-only verification.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "MANIFEST.sha256.asc" in output, output


def test_require_signature_is_fatal_without_keyring(tmp_path: Path) -> None:
    # Given: a valid unsigned bundle on a host without the provisioned release keyring.
    environment = prepare_bundle(tmp_path)
    write_manifest(tmp_path)

    # When: the operator requires detached signature verification.
    result = run_verification(tmp_path, environment, "--require-signature")

    # Then: the missing host trust anchor is fatal.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "/etc/blacklist/release-pubkey.gpg" in output, output


def test_mutating_install_always_requires_signature() -> None:
    installer_source = INSTALLER.read_text(encoding="utf-8")
    install_branch = installer_source.split('if [ "$verify_only" = true ]; then', 1)[1].split(
        "preflight_checks",
        1,
    )[0]

    assert "REQUIRE_SIGNATURE=true" in install_branch


def test_signature_verification_uses_host_keyring() -> None:
    # Given: the shipped installer source and the ADR-mandated trust anchor.
    installer_source = INSTALLER.read_text(encoding="utf-8")

    # When: the detached signature verifier is inspected.
    function_marker = "\nverify_manifest_signature() {"

    # Then: gpgv uses only the fixed host keyring and bundle signature inputs.
    assert function_marker in installer_source, installer_source
    function_body = installer_source.split(function_marker, 1)[1].split("\n}", 1)[0]
    assert 'gpgv --keyring "${RELEASE_KEYRING}" MANIFEST.sha256.asc MANIFEST.sha256' in function_body
    assert "BLACKLIST_RELEASE_KEYRING:-/etc/blacklist/release-pubkey.gpg" in installer_source
    assert '${SCRIPT_DIR}/release-pubkey.gpg' not in function_body
