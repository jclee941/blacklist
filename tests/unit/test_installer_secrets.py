from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest


INSTALLER = Path(__file__).parents[2] / "deploy" / "install.sh"
ENV_EXAMPLE = Path(__file__).parents[2] / "deploy" / ".env.example"
PRE_REDIS_REQUIRED_SECRETS = {
    "CREDENTIAL_MASTER_KEY": "local-credential-master-key-0123456789",
    "SECRET_KEY": "local-secret-key-0123456789",
    "CREDENTIAL_ENCRYPTION_KEY": "local-credential-encryption-key-0123456789",
    "ENCRYPTION_SALT": "local-encryption-salt-0123456789",
    "POSTGRES_PASSWORD": "local-postgres-password-0123456789",
}
REQUIRED_SECRETS_WITHOUT_COLLECTOR = {
    **PRE_REDIS_REQUIRED_SECRETS,
    "REDIS_PASSWORD": "local-redis-password-0123456789",
}
REQUIRED_SECRETS = {
    **REQUIRED_SECRETS_WITHOUT_COLLECTOR,
    "COLLECTOR_AUTH_TOKEN": "local-collector-auth-token-0123456789",
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD": "local-admin-password-0123456789",
}


def write_manifest(bundle_dir: Path) -> None:
    manifest = bundle_dir / "MANIFEST.sha256"
    manifest.unlink(missing_ok=True)
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
        + path.relative_to(bundle_dir).as_posix()
        for path in sorted(bundle_dir.rglob("*"))
        if path.is_file()
    ]
    _ = manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_secret_check(tmp_path: Path, env_file: Path) -> subprocess.CompletedProcess[str]:
    installer = tmp_path / "install.sh"
    _ = shutil.copy2(INSTALLER, installer)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    _ = docker.write_text(
        """#!/bin/sh
case "${1:-}" in
    ps)
        printf ''
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
    environment["BLACKLIST_ENV_FILE"] = str(env_file)
    write_manifest(tmp_path)
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


def test_redis_password_is_a_required_secret(tmp_path: Path) -> None:
    # Given: an environment file holding every previously required secret but no Redis password.
    env_file = tmp_path / ".env"
    original = "\n".join(
        f'{key}="{value}"' for key, value in sorted(PRE_REDIS_REQUIRED_SECRETS.items())
    ) + "\n"
    _ = env_file.write_text(original, encoding="utf-8")

    # When: bootstrap secret validation runs against that file.
    result = run_secret_check(tmp_path, env_file)

    # Then: installation is blocked and the missing Redis password is named.
    assert result.returncode != 0, result.stdout + result.stderr
    assert "REDIS_PASSWORD" in result.stdout + result.stderr


def test_collector_auth_token_is_a_required_secret(tmp_path: Path) -> None:
    # Given: an environment file holding every other required secret but no collector token.
    env_file = tmp_path / ".env"
    original = "\n".join(
        f'{key}="{value}"' for key, value in sorted(REQUIRED_SECRETS_WITHOUT_COLLECTOR.items())
    ) + "\n"
    _ = env_file.write_text(original, encoding="utf-8")

    # When: bootstrap secret validation runs against that file.
    result = run_secret_check(tmp_path, env_file)

    # Then: installation is blocked and the missing collector token is named.
    assert result.returncode != 0, result.stdout + result.stderr
    assert "COLLECTOR_AUTH_TOKEN" in result.stdout + result.stderr


@pytest.mark.parametrize("missing_key", ["ADMIN_USERNAME", "ADMIN_PASSWORD"])
def test_admin_credentials_are_required_secrets(tmp_path: Path, missing_key: str) -> None:
    env_file = tmp_path / ".env"
    body = "\n".join(
        f'{key}="{value}"' for key, value in sorted(REQUIRED_SECRETS.items()) if key != missing_key
    )
    _ = env_file.write_text(body + "\n", encoding="utf-8")

    result = run_secret_check(tmp_path, env_file)

    assert result.returncode != 0, result.stdout + result.stderr
    assert missing_key in result.stdout + result.stderr


def test_env_example_contains_only_admin_placeholders() -> None:
    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()

    assert lines.count("ADMIN_USERNAME=") == 1
    assert lines.count("ADMIN_PASSWORD=") == 1


def test_env_file_defaults_outside_bundle() -> None:
    # Given: the installer script as shipped inside the extracted release bundle.
    installer_source = INSTALLER.read_text(encoding="utf-8")

    # When: the environment file location is resolved.
    resolved_env_file = '"${BLACKLIST_ENV_FILE:-/etc/blacklist/.env}"'

    # Then: generated secrets land outside the bundle and stay operator-overridable.
    assert resolved_env_file in installer_source
    assert '"${SCRIPT_DIR}/.env"' not in installer_source


def test_env_file_override_is_honoured(tmp_path: Path) -> None:
    # Given: an operator-controlled secret location outside the extracted bundle.
    env_file = tmp_path / "etc" / "blacklist" / ".env"

    # When: bootstrap secret setup runs with that location configured.
    result = run_secret_check(tmp_path, env_file)

    # Then: the configured file holds the generated secrets and the bundle stays clean.
    assert result.returncode == 0, result.stdout + result.stderr
    assert env_file.exists(), "installer ignored BLACKLIST_ENV_FILE"
    generated_values = parse_env(env_file)
    assert "REDIS_PASSWORD" in generated_values
    assert os.stat(env_file).st_mode & 0o777 == 0o600
    assert not (tmp_path / ".env").exists()
