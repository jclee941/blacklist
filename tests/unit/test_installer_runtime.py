from __future__ import annotations

import hashlib
import os
import re
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
NON_ADMIN_SECRET_KEYS = (
    "CREDENTIAL_MASTER_KEY",
    "SECRET_KEY",
    "CREDENTIAL_ENCRYPTION_KEY",
    "ENCRYPTION_SALT",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "COLLECTOR_AUTH_TOKEN",
)


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
    manifest = bundle_dir / "MANIFEST.sha256"
    manifest.unlink(missing_ok=True)
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  " + path.relative_to(bundle_dir).as_posix()
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


def installer_function(name: str) -> str:
    source = INSTALLER.read_text(encoding="utf-8")
    return source.split(f"\n{name}() {{", 1)[1].split("\n}", 1)[0]


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


def test_generated_env_contains_unique_high_entropy_admin_passwords(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_env_file, first_environment = prepare_bundle(first_dir)
    second_env_file, second_environment = prepare_bundle(second_dir)

    first_result = run_installer(first_dir, first_environment, "--check-secrets")
    second_result = run_installer(second_dir, second_environment, "--check-secrets")

    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    first_values = parse_env(first_env_file)
    second_values = parse_env(second_env_file)
    assert first_values["ADMIN_USERNAME"] == "admin"
    assert second_values["ADMIN_USERNAME"] == "admin"
    first_password = first_values["ADMIN_PASSWORD"]
    second_password = second_values["ADMIN_PASSWORD"]
    assert re.fullmatch(r"[0-9a-f]{64}", first_password)
    assert re.fullmatch(r"[0-9a-f]{64}", second_password)
    assert first_password != second_password


def test_admin_password_is_displayed_once_without_other_secrets(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    env_file, environment = prepare_bundle(bundle_dir)

    first_result = run_installer(bundle_dir, environment, "--check-secrets")
    generated_values = parse_env(env_file)
    second_result = run_installer(bundle_dir, environment, "--check-secrets")

    assert first_result.returncode == 0, first_result.stdout + first_result.stderr
    assert second_result.returncode == 0, second_result.stdout + second_result.stderr
    admin_password = generated_values["ADMIN_PASSWORD"]
    assert admin_password in first_result.stdout
    assert admin_password not in second_result.stdout
    assert all(generated_values[key] not in first_result.stdout for key in NON_ADMIN_SECRET_KEYS)


def test_initial_admin_password_is_shown_after_health_checks() -> None:
    installer_source = INSTALLER.read_text(encoding="utf-8")
    main_body = installer_source.split("\nmain() {", 1)[1]

    health_index = main_body.rfind("health_checks")
    completion_index = main_body.rfind('log_success "Installation completed!"')
    password_index = main_body.rfind("show_initial_admin_password")

    assert health_index < completion_index < password_index


def test_health_regex_rejects_error_payload() -> None:
    # Given: the literal response pattern used by the installer's published health probe.
    health_body = installer_function("health_checks")
    pattern_match = re.search(r"grep (?:-q|-Eq) ([\"'])(?P<pattern>.*?)\1", health_body)
    assert pattern_match is not None, health_body
    pattern = pattern_match.group("pattern")

    # When: representative unhealthy and healthy JSON payloads are checked with that ERE.
    outcomes = {
        payload: subprocess.run(
            ["grep", "-Eq", pattern],
            input=payload,
            check=False,
            text=True,
        ).returncode
        for payload in (
            '{"status":"error"}',
            '{"status":"healthy"}',
            '{"status": "healthy"}',
        )
    }

    # Then: only the exact healthy status is accepted, regardless of JSON spacing.
    assert outcomes['{"status":"error"}'] == 1
    assert outcomes['{"status":"healthy"}'] == 0
    assert outcomes['{"status": "healthy"}'] == 0


def test_health_check_does_not_probe_unpublished_ports() -> None:
    # Given: ADR-0001 leaves the Flask and collector ports unpublished on the host.
    health_body = installer_function("health_checks")

    # When: the host-side health probes are inspected.

    # Then: neither internal-only service port is called through localhost.
    assert "localhost:2542" not in health_body
    assert "localhost:8545" not in health_body


def test_images_are_not_retagged_latest() -> None:
    # Given: the image loading and generated-environment paths in the offline installer.
    installer_source = INSTALLER.read_text(encoding="utf-8")
    generated_env_body = installer_function("generate_env_file")

    # When: release tag handling is inspected.

    # Then: no image is aliased to latest and Compose receives the bundle version.
    assert 'docker tag "$loaded_image" "${repo}:latest"' not in installer_source
    assert "BLACKLIST_VERSION=${VERSION}" in generated_env_body


def test_generated_environment_defaults_warp_to_disabled() -> None:
    generated_env_body = installer_function("generate_env_file")

    assert "WARP_ENABLED=false" in generated_env_body
    assert "WARP_PROXY_URL=" in generated_env_body


def test_warp_settings_are_synced_during_secret_setup() -> None:
    setup_body = installer_function("setup_secrets")
    sync_body = installer_function("sync_warp_settings")

    assert 'sync_warp_settings "${env_file}"' in setup_body
    assert "WARP_ENABLED=%s" in sync_body
    assert "WARP_PROXY_URL=%s" in sync_body


def test_rollback_file_is_not_written() -> None:
    # Given: the offline installer has no rollback-file reader.
    installer_source = INSTALLER.read_text(encoding="utf-8")

    # When: its deployment path is inspected.

    # Then: it does not advertise a dead recovery artifact by writing one.
    assert ".rollback-images" not in installer_source


def test_loaded_image_parsing_avoids_pcre() -> None:
    # Given: realistic docker load output with a layer line that is not an image result.
    installer_source = INSTALLER.read_text(encoding="utf-8")
    load_body = installer_function("load_images")
    docker_output = "\n".join(
        (
            "Loaded layer: sha256:decoy",
            "Loaded image: blacklist-app:4.1.0",
            "",
        )
    )

    # When: the installer's POSIX sed expression parses the output.
    assert "grep -oP" not in installer_source
    expression_match = re.search(r"sed -n '([^']+)'", load_body)
    assert expression_match is not None, load_body
    result = subprocess.run(
        ["sed", "-n", expression_match.group(1)],
        input=docker_output,
        capture_output=True,
        check=False,
        text=True,
    )

    # Then: only the loaded image name is returned and an empty result remains fatal.
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["blacklist-app:4.1.0"]
    assert 'if [ -z "${loaded_image}" ]; then' in load_body


def test_health_wait_polls_instead_of_sleeping() -> None:
    # Given: the installer must allow more than the app's 90-second start period.
    installer_source = INSTALLER.read_text(encoding="utf-8")

    # When: deployment readiness handling is inspected.
    assert "sleep 30" not in installer_source
    assert "\nwait_for_health() {" in installer_source
    wait_body = installer_function("wait_for_health")
    deploy_body = installer_function("deploy_services")
    timeout_match = re.search(r"readonly HEALTH_WAIT_TIMEOUT_SECONDS=(\d+)", installer_source)
    assert timeout_match is not None, installer_source

    # Then: all five services use Docker health with a sufficient bounded deadline.
    assert int(timeout_match.group(1)) >= 180
    assert "docker inspect -f '{{.State.Health.Status}}'" in wait_body
    assert 'wait_for_health "${containers[@]}"' in deploy_body
    assert "<no value>" in wait_body
    assert 'log_info "${container}: last status ${last_status[' in wait_body
    for container in (
        "blacklist-app",
        "blacklist-collector",
        "blacklist-frontend",
        "blacklist-postgres",
        "blacklist-redis",
    ):
        assert container in deploy_body
