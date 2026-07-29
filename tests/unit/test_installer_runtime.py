from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path


INSTALLER = Path(__file__).parents[2] / "deploy" / "install.sh"
BUNDLE_IMAGES = (
    "blacklist-app.tar.gz",
    "blacklist-collector.tar.gz",
    "blacklist-frontend.tar.gz",
    "blacklist-postgres.tar.gz",
    "blacklist-redis.tar.gz",
)
FAKE_DOCKER = """#!/bin/sh
case "${1:-}" in
    ps)
        printf ''
        ;;
    *)
        exit 1
        ;;
esac
"""
FAKE_SS = """#!/bin/sh
exit 0
"""


def prepare_bundle(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    tmp_path.mkdir(parents=True)
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
    _ = (tmp_path / "VERSION").write_text("4.1.0\n", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for executable_name, source in (("docker", FAKE_DOCKER), ("ss", FAKE_SS)):
        executable = bin_dir / executable_name
        _ = executable.write_text(source, encoding="utf-8")
        _ = executable.chmod(0o755)

    env_file = tmp_path / "etc" / "blacklist" / ".env"
    environment = os.environ.copy()
    environment["PATH"] = f"{bin_dir}{os.pathsep}{environment['PATH']}"
    environment["BLACKLIST_ENV_FILE"] = str(env_file)
    return env_file, environment


def write_manifest(bundle_dir: Path) -> None:
    """Regenerate MANIFEST.sha256 from the bundle's CURRENT contents."""
    manifest = bundle_dir / "MANIFEST.sha256"
    manifest.unlink(missing_ok=True)
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
        + path.relative_to(bundle_dir).as_posix()
        for path in sorted(bundle_dir.rglob("*"))
        if path.is_file()
    ]
    _ = manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_installer(
    bundle_dir: Path,
    environment: dict[str, str],
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    write_manifest(bundle_dir)
    return subprocess.run(
        ["bash", str(bundle_dir / "install.sh"), *arguments],
        cwd=bundle_dir,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )


def parse_env(env_file: Path) -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in env_file.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )


def test_generated_env_contains_a_collector_token(tmp_path: Path) -> None:
    # Given: two fresh offline bundles with separate target environment files.
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_env_file, first_environment = prepare_bundle(first_dir)
    second_env_file, second_environment = prepare_bundle(second_dir)

    # When: bootstrap secret generation runs independently for each target.
    first_result = run_installer(first_dir, first_environment, "--check-secrets")
    second_result = run_installer(second_dir, second_environment, "--check-secrets")

    # Then: each target receives a non-empty, independently generated collector token.
    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    first_token = parse_env(first_env_file)["COLLECTOR_AUTH_TOKEN"]
    second_token = parse_env(second_env_file)["COLLECTOR_AUTH_TOKEN"]
    assert first_token
    assert second_token
    assert first_token != second_token
