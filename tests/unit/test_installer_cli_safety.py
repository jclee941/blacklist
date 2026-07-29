from __future__ import annotations

import gzip
import os
import shutil
import subprocess
from pathlib import Path


INSTALLER = Path(__file__).parents[2] / "deploy" / "install.sh"
BUNDLE_IMAGES = (
    "app.tar.gz",
    "collector.tar.gz",
    "frontend.tar.gz",
    "postgres.tar.gz",
    "redis.tar.gz",
)
FAKE_DOCKER = """#!/bin/sh
printf '%s\\n' "$*" >> "${TEST_DOCKER_LOG}"
case "${1:-}" in
    --version) echo "Docker version 27.0.0, build test" ;;
    compose)
        if [ "${2:-}" = "version" ]; then
            echo "2.29.0"
        fi
        ;;
    volume) exit 1 ;;
esac
exit 0
"""
FAKE_SLEEP = """#!/bin/sh
exit 0
"""


def run_installer(tmp_path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    installer = tmp_path / "install.sh"
    _ = shutil.copy2(INSTALLER, installer)

    return subprocess.run(
        ["bash", str(installer), *arguments],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )


def prepare_bundle(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    installer = tmp_path / "install.sh"
    _ = shutil.copy2(INSTALLER, installer)

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    for image_name in BUNDLE_IMAGES:
        _ = (images_dir / image_name).write_bytes(gzip.compress(b"fake-image-archive"))
    _ = (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    _ = docker.write_text(FAKE_DOCKER, encoding="utf-8")
    _ = docker.chmod(0o755)
    sleeper = bin_dir / "sleep"
    _ = sleeper.write_text(FAKE_SLEEP, encoding="utf-8")
    _ = sleeper.chmod(0o755)

    docker_log = tmp_path / "docker.log"
    environment = os.environ.copy()
    environment["PATH"] = f"{bin_dir}{os.pathsep}{environment['PATH']}"
    environment["TEST_DOCKER_LOG"] = str(docker_log)
    environment["BLACKLIST_ENV_FILE"] = str(tmp_path / "etc" / ".env")
    return installer, docker_log, environment


def root_refusals(output: str) -> list[str]:
    return [
        line
        for line in output.splitlines()
        if "[ERROR]" in line and ("root" in line.lower() or "euid" in line.lower())
    ]


def test_installer_syntax_is_valid() -> None:
    # Given: the offline installer as shipped inside the release bundle.

    # When: the shell parses the script without executing it.
    result = subprocess.run(["bash", "-n", str(INSTALLER)], capture_output=True, check=False, text=True)

    # Then: the script is syntactically valid.
    assert result.returncode == 0, result.stdout + result.stderr


def test_help_lists_new_flags(tmp_path: Path) -> None:
    # Given: an operator without root privileges reading the installer usage.

    # When: help is requested.
    result = run_installer(tmp_path, "--help")

    # Then: the read-only verification mode is documented.
    assert result.returncode == 0, result.stdout + result.stderr
    assert "--verify-only" in result.stdout


def test_install_requires_root(tmp_path: Path) -> None:
    # Given: a complete release bundle driven by an unprivileged operator.
    installer, docker_log, environment = prepare_bundle(tmp_path)

    # When: the default installation path runs without root privileges.
    result = subprocess.run(
        ["bash", str(installer)],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    # Then: the installer refuses, naming the privilege it needs.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert root_refusals(output), output

    # Then: it refused before doing any work, so no image was ever loaded.
    performed = docker_log.read_text(encoding="utf-8") if docker_log.exists() else ""
    assert "load" not in performed, performed


def test_check_secrets_still_runs_without_root(tmp_path: Path) -> None:
    # Given: an unprivileged operator preparing secrets ahead of installation.
    installer, _, environment = prepare_bundle(tmp_path)

    # When: only the secret bootstrap is requested.
    result = subprocess.run(
        ["bash", str(installer), "--check-secrets"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    # Then: the privilege gate never blocks this unprivileged entry point.
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert root_refusals(output) == [], output
    assert Path(environment["BLACKLIST_ENV_FILE"]).exists(), output
