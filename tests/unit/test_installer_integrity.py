from __future__ import annotations

import hashlib
import os
import shutil
import socket
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


def write_manifest(bundle_dir: Path) -> None:
    """Regenerate MANIFEST.sha256 from the bundle's CURRENT contents.

    The shipped 4.1.0 manifest covers images/** including checksums.sha256, so a
    manifest captured before a test tampers with those files would fail first and
    the checksum layer under test would never run. Regenerating here models a
    well-formed bundle whose manifest matches its own contents, which is the
    precondition for exercising verify_checksums().
    """
    manifest = bundle_dir / "MANIFEST.sha256"
    manifest.unlink(missing_ok=True)
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
        f"{path.relative_to(bundle_dir).as_posix()}"
        for path in sorted(bundle_dir.rglob("*"))
        if path.is_file()
    ]
    _ = manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_verification(tmp_path: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    write_manifest(tmp_path)
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


def test_disk_check_targets_the_docker_data_dir() -> None:
    # Given: the installer shipped with the offline bundle.
    installer_source = INSTALLER.read_text(encoding="utf-8")

    # When: the disk-capacity check is inspected.

    # Then: DockerRootDir selects the filesystem passed to df.
    assert "docker info --format '{{.DockerRootDir}}'" in installer_source
    assert 'df -BG "${disk_target}"' in installer_source


def test_disk_check_survives_unparsable_output(tmp_path: Path) -> None:
    # Given: Docker is installed but returns no data directory from docker info.
    images_dir, environment = prepare_bundle(tmp_path)
    write_checksum_file(images_dir, BUNDLE_IMAGES)
    docker_log = tmp_path / "docker.log"
    docker = tmp_path / "bin" / "docker"
    _ = docker.write_text(
        """#!/bin/sh
printf '%s\n' "$*" >> "${TEST_DOCKER_LOG}"
exit 0
""",
        encoding="utf-8",
    )
    _ = docker.chmod(0o755)
    environment["TEST_DOCKER_LOG"] = str(docker_log)

    # When: the read-only bundle verification runs.
    result = run_verification(tmp_path, environment)

    # Then: it falls back without reaching an invalid integer comparison.
    output = result.stdout + result.stderr
    performed = docker_log.read_text(encoding="utf-8") if docker_log.exists() else ""
    assert result.returncode == 0, output
    assert "integer expression expected" not in output, output
    assert "info --format {{.DockerRootDir}}" in performed, performed


def test_published_port_occupancy_is_fatal(tmp_path: Path) -> None:
    # Given: a process already listening on the port the test bundle publishes.
    published_port = 44443
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", published_port))
        listener.listen()

        images_dir, environment = prepare_bundle(tmp_path)
        write_checksum_file(images_dir, BUNDLE_IMAGES)
        (tmp_path / "bin" / "ss").unlink()

        installer = tmp_path / "install.sh"
        installer_source = installer.read_text(encoding="utf-8")
        configured_source = installer_source.replace(
            "readonly PUBLISHED_FRONTEND_PORT=443",
            f"readonly PUBLISHED_FRONTEND_PORT={published_port}",
        ).replace(
            "for port in 443 2542 5432 6379 8545; do",
            f"for port in {published_port}; do",
        )
        assert configured_source != installer_source
        _ = installer.write_text(configured_source, encoding="utf-8")

        # When: the read-only bundle verification checks that occupied port.
        result = run_verification(tmp_path, environment)

    # Then: occupancy is fatal, scoped to the frontend, and checked after upgrade removal.
    output = result.stdout + result.stderr
    shipped_source = INSTALLER.read_text(encoding="utf-8")
    deploy_body = shipped_source.split("\ndeploy_services() {", 1)[1].split("\n}", 1)[0]
    assert result.returncode != 0, output
    assert str(published_port) in output, output
    assert "for port in 443 2542 5432 6379 8545; do" not in shipped_source
    assert deploy_body.index('docker rm -f "$c"') < deploy_body.index("verify_published_port_available")
    assert deploy_body.index("verify_published_port_available") < deploy_body.index('log_info "Starting services..."')
