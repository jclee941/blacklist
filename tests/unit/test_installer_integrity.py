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
FAKE_SS = """#!/bin/sh
exit 0
"""


def prepare_bundle(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    installer = tmp_path / "install.sh"
    _ = shutil.copy2(INSTALLER, installer)

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    for image_name in BUNDLE_IMAGES:
        _ = (images_dir / image_name).write_bytes(f"payload:{image_name}".encode())

    _ = (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")

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
    return images_dir, environment


def checksum_line(payload: Path, listed_name: str) -> str:
    checksum = hashlib.sha256(payload.read_bytes()).hexdigest()
    separator = " " if listed_name.startswith("*") else "  "
    return f"{checksum}{separator}{listed_name}\n"


def write_checksum_file(images_dir: Path, listed_names: tuple[str, ...]) -> None:
    lines: list[str] = []
    for listed_name in listed_names:
        payload_name = listed_name.removeprefix("*").removeprefix("./")
        lines.append(checksum_line(images_dir / payload_name, listed_name))
    _ = (images_dir / "checksums.sha256").write_text("".join(lines), encoding="utf-8")


def run_verification(tmp_path: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(tmp_path / "install.sh"), "--verify-only", "--skip-posture-check"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )


def test_missing_listed_file_is_fatal(tmp_path: Path) -> None:
    # Given: a checksum list containing one real image and one absent image.
    images_dir, environment = prepare_bundle(tmp_path)
    real_image = images_dir / BUNDLE_IMAGES[0]
    ghost_checksum = hashlib.sha256(b"missing-payload").hexdigest()
    checksum_text = checksum_line(real_image, real_image.name)
    checksum_text += f"{ghost_checksum}  ghost.tar.gz\n"
    _ = (images_dir / "checksums.sha256").write_text(checksum_text, encoding="utf-8")

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: the absent listed image is named and verification cannot report success.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "ghost.tar.gz" in output, output
    assert "All checksums verified" not in output, output


def test_absent_checksum_file_is_fatal(tmp_path: Path) -> None:
    # Given: a complete image set without its checksum list.
    _, environment = prepare_bundle(tmp_path)

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: installation is refused instead of silently skipping integrity checks.
    assert result.returncode != 0, result.stdout + result.stderr


def test_empty_checksum_file_is_fatal(tmp_path: Path) -> None:
    # Given: a complete image set with a zero-byte checksum list.
    images_dir, environment = prepare_bundle(tmp_path)
    _ = (images_dir / "checksums.sha256").write_bytes(b"")

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: verifying zero payloads is fatal.
    assert result.returncode != 0, result.stdout + result.stderr


def test_corrupted_payload_is_fatal(tmp_path: Path) -> None:
    # Given: a valid checksum list whose first payload is mutated afterwards.
    images_dir, environment = prepare_bundle(tmp_path)
    write_checksum_file(images_dir, BUNDLE_IMAGES)
    with (images_dir / BUNDLE_IMAGES[0]).open("ab") as payload:
        _ = payload.write(b"corruption")

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: the corrupted image is refused.
    assert result.returncode != 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "listed_name",
    [
        "blacklist-app.tar.gz",
        "./blacklist-app.tar.gz",
        "*blacklist-app.tar.gz",
    ],
)
def test_checksum_names_are_normalised(tmp_path: Path, listed_name: str) -> None:
    # Given: a checksum emitted by one of the supported real bundle producers.
    images_dir, environment = prepare_bundle(tmp_path)
    write_checksum_file(images_dir, (listed_name,))

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: every producer spelling resolves to the same shipped image.
    assert result.returncode == 0, result.stdout + result.stderr


def test_dual_filename_tolerance_is_removed() -> None:
    # Given: the installer shipped with the offline bundle.
    installer_source = INSTALLER.read_text(encoding="utf-8")

    # When: image lookup paths are inspected.
    bare_preflight_lookup = 'if [ -f "${IMAGES_DIR}/${img}" ]; then'
    bare_load_path = 'local img_path="${IMAGES_DIR}/${img}"'

    # Then: both call sites pin the measured blacklist-prefixed artifact names.
    assert bare_preflight_lookup not in installer_source
    assert bare_load_path not in installer_source
    assert installer_source.count('"${IMAGES_DIR}/blacklist-${img}"') >= 2
