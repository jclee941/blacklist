from __future__ import annotations

import hashlib
import importlib.util
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


def test_incomplete_prereqs_are_reported(tmp_path: Path) -> None:
    # Given: install_docker_offline() extracts prereqs/docker-*.tgz and copies the
    # compose binary as root on a host that has no Docker yet.
    builder = load_builder()
    prereqs = tmp_path / "prereqs"
    prereqs.mkdir()
    _ = (prereqs / "docker.service").write_text("[Unit]\n", encoding="utf-8")

    missing = builder.missing_prereqs(prereqs)

    # Then: shipping without them yields a bundle that cannot bootstrap a bare
    # host, which must not pass silently.
    assert "docker-*.tgz" in missing
    assert "docker-compose-linux-x86_64" in missing


def test_complete_prereqs_report_nothing_missing(tmp_path: Path) -> None:
    builder = load_builder()
    prereqs = tmp_path / "prereqs"
    prereqs.mkdir()
    _ = (prereqs / "docker.service").write_text("[Unit]\n", encoding="utf-8")
    _ = (prereqs / "docker-29.2.1.tgz").write_bytes(b"tarball")
    _ = (prereqs / "docker-compose-linux-x86_64").write_bytes(b"binary")

    assert builder.missing_prereqs(prereqs) == []
