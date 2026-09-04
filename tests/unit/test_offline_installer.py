from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


INSTALLER = Path(__file__).parents[2] / "deploy" / "install.sh"
REQUIRED_ENV_KEYS = {
    "ADMIN_PASSWORD",
    "ADMIN_USERNAME",
    "COLLECTOR_AUTH_TOKEN",
    "CREDENTIAL_MASTER_KEY",
    "SECRET_KEY",
    "FLASK_SECRET_KEY",
    "JWT_SECRET_KEY",
    "CREDENTIAL_ENCRYPTION_KEY",
    "SETTINGS_ENCRYPTION_KEY",
    "ENCRYPTION_SALT",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
}


def run_secret_check(
    tmp_path: Path,
    *,
    docker_ps_output: str = "",
    docker_volume_names: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    installer = tmp_path / "install.sh"
    _ = shutil.copy2(INSTALLER, installer)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    _ = docker.write_text(
        """#!/bin/sh
case \"${1:-}\" in
    ps)
        printf '%s' \"${TEST_DOCKER_PS_OUTPUT:-}\"
        ;;
    volume)
        case \" ${TEST_DOCKER_VOLUME_NAMES:-} \" in
            *\" ${3:-} \"*) exit 0 ;;
        esac
        exit 1
        ;;
    *)
        exit 1
        ;;
esac
""",
        encoding="utf-8",
    )
    _ = docker.chmod(0o755)

    environment = os.environ.copy()
    environment["PATH"] = f"{bin_dir}{os.pathsep}{environment['PATH']}"
    environment["TEST_DOCKER_PS_OUTPUT"] = docker_ps_output
    environment["TEST_DOCKER_VOLUME_NAMES"] = " ".join(docker_volume_names)
    environment["BLACKLIST_ENV_FILE"] = str(tmp_path / ".env")
    return subprocess.run(
        ["bash", str(installer), "--check-secrets"],
        cwd=tmp_path,
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


def test_generates_target_local_secrets_when_env_is_absent(tmp_path: Path) -> None:
    # Given: an offline installer directory without an environment file.

    # When: bootstrap secret setup runs.
    result = run_secret_check(tmp_path)

    # Then: all required values are generated locally and protected.
    env_file = tmp_path / ".env"
    assert result.returncode == 0, result.stdout + result.stderr
    generated_values = parse_env(env_file)
    assert REQUIRED_ENV_KEYS <= generated_values.keys()
    assert generated_values["ADMIN_USERNAME"] == "admin"
    assert generated_values["ADMIN_PASSWORD"]
    assert all(not value.startswith("op://") for value in generated_values.values())
    assert os.stat(env_file).st_mode & 0o777 == 0o600


def test_rejects_unresolved_secret_references_without_overwriting(tmp_path: Path) -> None:
    # Given: an existing file whose required values are unresolved references.
    env_file = tmp_path / ".env"
    original = "\n".join(f"{key}=op://offline/{key}" for key in sorted(REQUIRED_ENV_KEYS)) + "\n"
    _ = env_file.write_text(original, encoding="utf-8")

    # When: bootstrap secret validation runs.
    result = run_secret_check(tmp_path)

    # Then: startup is blocked, invalid names are reported, and the file is preserved.
    assert result.returncode != 0
    assert "CREDENTIAL_MASTER_KEY" in result.stdout
    assert "op://offline" not in result.stdout
    assert env_file.read_text(encoding="utf-8") == original
    assert os.stat(env_file).st_mode & 0o777 == 0o600


def test_rejects_missing_placeholders_expressions_empty_values_and_defaults(tmp_path: Path) -> None:
    # Given: an existing file containing every unsupported secret representation.
    env_file = tmp_path / ".env"
    original = "\n".join(
        (
            "CREDENTIAL_MASTER_KEY=__SET_CREDENTIAL_MASTER_KEY__",
            "SECRET_KEY=${SECRET_KEY}",
            "CREDENTIAL_ENCRYPTION_KEY=",
            "POSTGRES_PASSWORD=postgres",
        )
    ) + "\n"
    _ = env_file.write_text(original, encoding="utf-8")

    # When: bootstrap secret validation runs.
    result = run_secret_check(tmp_path)

    # Then: every invalid or missing key is named without changing the file.
    assert result.returncode != 0
    assert all(key in result.stdout for key in REQUIRED_ENV_KEYS)
    assert "__SET_CREDENTIAL_MASTER_KEY__" not in result.stdout
    assert "${SECRET_KEY}" not in result.stdout
    assert env_file.read_text(encoding="utf-8") == original
    assert os.stat(env_file).st_mode & 0o777 == 0o600


def test_preserves_valid_existing_secrets(tmp_path: Path) -> None:
    # Given: a complete literal environment file from a previous installation.
    env_file = tmp_path / ".env"
    original = "\n".join(
        (
            'CREDENTIAL_MASTER_KEY="local-credential-master-key-0123456789"',
            "SECRET_KEY='local-secret-key-0123456789'",
            "FLASK_SECRET_KEY='local-flask-secret-key-0123456789'",
            "JWT_SECRET_KEY='local-jwt-secret-key-0123456789'",
            'CREDENTIAL_ENCRYPTION_KEY="local-credential-encryption-key-0123456789"',
            'SETTINGS_ENCRYPTION_KEY="local-settings-encryption-key-0123456789"',
            "ENCRYPTION_SALT='local-encryption-salt-0123456789'",
            'POSTGRES_PASSWORD="local-postgres-password-0123456789"',
            'REDIS_PASSWORD="local-redis-password-0123456789"',
            'COLLECTOR_AUTH_TOKEN="local-collector-auth-token-0123456789"',
            'ADMIN_USERNAME="admin"',
            'ADMIN_PASSWORD="local-admin-password-0123456789"',
        )
    ) + "\n"
    _ = env_file.write_text(original, encoding="utf-8")

    # When: bootstrap secret validation runs during an upgrade.
    result = run_secret_check(tmp_path)

    # Then: every existing secret survives verbatim. Byte-identity is no longer the
    # right assertion because the installer re-pins the non-secret BLACKLIST_VERSION
    # on each run; assert the actual intent instead, and that no secret was added,
    # dropped, or rewritten.
    body = env_file.read_text(encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    runtime_settings = (
        "BLACKLIST_VERSION=",
        "WARP_ENABLED=",
        "WARP_PROXY_URL=",
        "FRONTEND_TLS_MODE=",
        "FRONTEND_BIND_ADDRESS=",
        "APP_DB_USER=",
        "APP_DB_PASSWORD=",
        "COLLECTOR_DB_USER=",
        "COLLECTOR_DB_PASSWORD=",
        "DB_OWNER_ROLE=",
    )
    surviving_secrets = [line for line in body.splitlines() if not line.startswith(runtime_settings)]
    assert surviving_secrets == original.splitlines()
    assert os.stat(env_file).st_mode & 0o777 == 0o600


def test_rejects_quoted_unresolved_secrets_without_exposing_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    original = "\n".join(
        (
            'CREDENTIAL_MASTER_KEY="local-credential-master-key-0123456789"',
            "SECRET_KEY='op://offline/secret-key'",
            'CREDENTIAL_ENCRYPTION_KEY="${CREDENTIAL_ENCRYPTION_KEY}"',
            "ENCRYPTION_SALT='local-encryption-salt-0123456789'",
            'POSTGRES_PASSWORD="local-postgres-password-0123456789"',
        )
    ) + "\n"
    _ = env_file.write_text(original, encoding="utf-8")

    result = run_secret_check(tmp_path)

    assert result.returncode != 0
    assert "SECRET_KEY" in result.stdout
    assert "CREDENTIAL_ENCRYPTION_KEY" in result.stdout
    assert "op://offline" not in result.stdout
    assert "${CREDENTIAL_ENCRYPTION_KEY}" not in result.stdout
    assert env_file.read_text(encoding="utf-8") == original
    assert os.stat(env_file).st_mode & 0o777 == 0o600


def test_rejects_duplicate_required_secret_key_without_overwriting(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    original = "\n".join(
        f"{key}=local-{key.lower()}-0123456789" for key in sorted(REQUIRED_ENV_KEYS)
    ) + "\nSECRET_KEY=another-local-secret-key-0123456789\n"
    _ = env_file.write_text(original, encoding="utf-8")

    result = run_secret_check(tmp_path)

    assert result.returncode != 0
    assert "SECRET_KEY" in result.stdout
    assert "another-local-secret-key" not in result.stdout
    assert env_file.read_text(encoding="utf-8") == original
    assert os.stat(env_file).st_mode & 0o777 == 0o600


def test_rejects_missing_env_when_existing_container_is_detected(tmp_path: Path) -> None:
    result = run_secret_check(tmp_path, docker_ps_output="existing-container")

    assert result.returncode != 0
    assert "existing deployment" in result.stdout.lower()
    assert not (tmp_path / ".env").exists()


def test_rejects_missing_env_when_existing_named_volume_is_detected(tmp_path: Path) -> None:
    result = run_secret_check(tmp_path, docker_volume_names=("blacklist_blacklist-pgdata",))

    assert result.returncode != 0
    assert "existing deployment" in result.stdout.lower()
    assert not (tmp_path / ".env").exists()


def test_starts_compose_without_pulling_images() -> None:
    # Given: the installer used inside a disconnected deployment environment.
    installer_source = INSTALLER.read_text(encoding="utf-8")

    # When: the Compose startup command is inspected.
    startup_command = (
        'docker compose --env-file "${ENV_FILE}" -f "${SCRIPT_DIR}/docker-compose.yml" '
        "up -d --pull never"
    )

    # Then: startup is constrained to the images loaded from the release bundle.
    assert startup_command in installer_source
