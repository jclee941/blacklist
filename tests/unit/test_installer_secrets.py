from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


INSTALLER = Path(__file__).parents[2] / "deploy" / "install.sh"
PRE_REDIS_REQUIRED_SECRETS = {
    "CREDENTIAL_MASTER_KEY": "local-credential-master-key-0123456789",
    "SECRET_KEY": "local-secret-key-0123456789",
    "CREDENTIAL_ENCRYPTION_KEY": "local-credential-encryption-key-0123456789",
    "ENCRYPTION_SALT": "local-encryption-salt-0123456789",
    "POSTGRES_PASSWORD": "local-postgres-password-0123456789",
}


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
    return subprocess.run(
        ["bash", str(installer), "--check-secrets"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
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
