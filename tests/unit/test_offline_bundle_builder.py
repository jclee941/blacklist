from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parents[2]
BUILDER_PATH = REPO_ROOT / "scripts" / "build_offline_bundle.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("build_offline_bundle", BUILDER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_offline_bundle"] = module
    spec.loader.exec_module(module)
    return module


def test_version_is_resolved_automatically(tmp_path: Path) -> None:
    # Given: the repository records its version in one place.
    builder = load_builder()
    _ = (tmp_path / "VERSION").write_text("7.3.1\n", encoding="utf-8")
    # Then: the bundle version is derived from it, never passed by hand.
    assert builder.resolve_version(tmp_path) == "7.3.1"


def test_missing_version_is_fatal(tmp_path: Path) -> None:
    builder = load_builder()
    with pytest.raises(builder.BundleError):
        _ = builder.resolve_version(tmp_path)


def test_checksums_use_bare_filenames(tmp_path: Path) -> None:
    # Given: the shipped 4.1.0 bundle records bare names with a two-space
    # separator and no binary-mode marker.
    builder = load_builder()
    images = tmp_path / "images"
    images.mkdir()
    payload = b"image-payload"
    _ = (images / "blacklist-app.tar.gz").write_bytes(payload)

    builder.write_image_checksums(images)

    line = (images / "checksums.sha256").read_text(encoding="utf-8").strip()
    assert line == f"{hashlib.sha256(payload).hexdigest()}  blacklist-app.tar.gz"
    assert "./" not in line
    assert "*" not in line


def test_manifest_covers_every_file_except_itself(tmp_path: Path) -> None:
    # Given: install.sh treats a missing or mismatched manifest as fatal, and the
    # shipped manifest includes images/** while excluding itself.
    builder = load_builder()
    (tmp_path / "images").mkdir()
    _ = (tmp_path / "install.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    _ = (tmp_path / "VERSION").write_text("7.3.1\n", encoding="utf-8")
    _ = (tmp_path / "images" / "blacklist-app.tar.gz").write_bytes(b"payload")

    builder.write_manifest(tmp_path)

    recorded = {
        line.split("  ", 1)[1]
        for line in (tmp_path / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    }
    assert recorded == {"install.sh", "VERSION", "images/blacklist-app.tar.gz"}
    assert "MANIFEST.sha256" not in recorded


def test_manifest_paths_are_bare_and_verifiable(tmp_path: Path) -> None:
    # Given: install.sh verifies the manifest with `sha256sum -c` from the bundle
    # root, so a ./ prefix or a stale hash rejects a valid bundle.
    import subprocess

    builder = load_builder()
    _ = (tmp_path / "install.sh").write_text("#!/bin/bash\nVERSION=7.3.1\n", encoding="utf-8")

    builder.write_manifest(tmp_path)

    body = (tmp_path / "MANIFEST.sha256").read_text(encoding="utf-8")
    assert "./" not in body
    result = subprocess.run(
        ["sha256sum", "-c", "--strict", "MANIFEST.sha256"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_installer_version_is_stamped_before_the_manifest(tmp_path: Path) -> None:
    # Given: the bundle's install.sh is rewritten to carry the release version.
    # Then: hashing it before that rewrite would record a stale hash and make
    # every install abort on manifest verification.
    builder = load_builder()
    installer = tmp_path / "install.sh"
    _ = installer.write_text(
        '#!/bin/bash\nVERSION=$(cat "${SCRIPT_DIR}/VERSION" 2>/dev/null || echo \'unknown\')\n',
        encoding="utf-8",
    )

    builder.stamp_installer_version(installer, "7.3.1")
    builder.write_manifest(tmp_path)

    assert "VERSION=7.3.1" in installer.read_text(encoding="utf-8")
    recorded = dict(
        line.split("  ", 1)[::-1]
        for line in (tmp_path / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    )
    assert recorded["install.sh"] == hashlib.sha256(installer.read_bytes()).hexdigest()


def test_absent_prereqs_are_not_a_defect(tmp_path: Path) -> None:
    # Given: the target host is assumed to already have Docker, so the offline
    # Docker installer payload is deliberately not shipped.
    builder = load_builder()
    prereqs = tmp_path / "prereqs"
    prereqs.mkdir()
    _ = (prereqs / "docker.service").write_text("[Unit]\n", encoding="utf-8")

    # Then: a bundle without them is complete, not broken.
    assert builder.prereq_gaps(prereqs) == []


def test_partial_prereqs_are_reported(tmp_path: Path) -> None:
    # Given: a bundle that ships SOME of the offline Docker payload.
    builder = load_builder()
    prereqs = tmp_path / "prereqs"
    prereqs.mkdir()
    _ = (prereqs / "docker.service").write_text("[Unit]\n", encoding="utf-8")
    _ = (prereqs / "docker-29.2.1.tgz").write_bytes(b"tarball")

    gaps = builder.prereq_gaps(prereqs)

    # Then: the half-shipped state is a real defect. install_docker_offline()
    # would extract the tarball as root and then fail on the missing binary,
    # leaving the host partially modified.
    assert gaps == ["docker-compose-linux-x86_64"]


def test_complete_prereqs_report_no_gaps(tmp_path: Path) -> None:
    builder = load_builder()
    prereqs = tmp_path / "prereqs"
    prereqs.mkdir()
    _ = (prereqs / "docker.service").write_text("[Unit]\n", encoding="utf-8")
    _ = (prereqs / "docker-29.2.1.tgz").write_bytes(b"tarball")
    _ = (prereqs / "docker-compose-linux-x86_64").write_bytes(b"binary")

    assert builder.prereq_gaps(prereqs) == []


def test_build_specs_mirror_the_ci_matrix() -> None:
    # Given: images must be built exactly as the release pipeline builds them,
    # or the bundle ships something that was never tested.
    builder = load_builder()
    specs = {spec.service: spec for spec in builder.BUILD_SPECS}

    assert set(specs) == set(builder.SERVICES)
    assert specs["frontend"].dockerfile == "frontend/Dockerfile"
    assert specs["app"].dockerfile == "app/Dockerfile"
    assert specs["collector"].dockerfile == "collector/Dockerfile"
    assert specs["postgres"].dockerfile == "postgres/Dockerfile"
    assert specs["redis"].dockerfile == "deploy/redis/Dockerfile"
    # postgres builds from its own directory in CI; everything else from the root.
    assert specs["postgres"].context == "postgres"
    assert specs["app"].context == "."


def test_build_command_tags_the_resolved_version() -> None:
    builder = load_builder()
    spec = next(spec for spec in builder.BUILD_SPECS if spec.service == "app")

    command = builder.build_command(spec, "7.3.1", "abc1234")

    assert "blacklist-app:7.3.1" in command
    assert "APP_VERSION=7.3.1" in " ".join(command)
    assert "GIT_COMMIT=abc1234" in " ".join(command)


def test_bundle_ships_every_compose_bind_mount_source(tmp_path: Path) -> None:
    # Given: base.yml bind-mounts deployment assets by relative path.
    builder = load_builder()
    deploy = REPO_ROOT / "deploy"
    base = (deploy / "base.yml").read_text(encoding="utf-8")
    relative_sources = set(re.findall(r"-\s+\./([\w./-]+):", base))
    assert relative_sources, "expected at least one relative bind mount in base.yml"

    bundle = tmp_path / "bundle"
    builder.assemble(REPO_ROOT, bundle, "9.9.9")

    # Then: every one must exist in the bundle. A missing source makes Docker
    # silently create an empty DIRECTORY at that path, and the container fails
    # at runtime instead of at packaging time.
    for source in sorted(relative_sources):
        assert (bundle / source).is_file(), f"{source} is not shipped in the bundle"


def test_bundle_ships_release_notes_for_the_declared_version(tmp_path: Path) -> None:
    # Given: operators upgrading an air-gapped site read RELEASE_NOTES.md from the
    # bundle. assemble() copies it only when a version-matched file exists, so a
    # missing one is silently omitted rather than reported.
    builder = load_builder()
    version = builder.resolve_version(REPO_ROOT)
    notes = REPO_ROOT / "docs" / "manual" / f"blacklist-{version}-release-notes.md"
    assert notes.is_file(), f"{notes} is missing for VERSION {version}"

    bundle = tmp_path / "bundle"
    builder.assemble(REPO_ROOT, bundle, version)

    assert (bundle / "RELEASE_NOTES.md").is_file()
