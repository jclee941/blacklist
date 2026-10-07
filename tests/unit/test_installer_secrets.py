from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


INSTALLER = Path(__file__).parents[2] / "deploy" / "install.sh"
INIT_SECRETS = Path(__file__).parents[2] / "deploy" / "init-secrets.sh"
ENV_EXAMPLE = Path(__file__).parents[2] / "deploy" / ".env.example"
PRE_REDIS_REQUIRED_SECRETS = {
    "CREDENTIAL_MASTER_KEY": "local-credential-master-key-0123456789",
    "SECRET_KEY": "local-secret-key-0123456789",
    "FLASK_SECRET_KEY": "local-flask-secret-key-0123456789",
    "JWT_SECRET_KEY": "local-jwt-secret-key-0123456789",
    "CREDENTIAL_ENCRYPTION_KEY": "local-credential-encryption-key-0123456789",
    "ENCRYPTION_SALT": "local-encryption-salt-0123456789",
    "SETTINGS_ENCRYPTION_KEY": "local-settings-encryption-key-0123456789",
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
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  " + path.relative_to(bundle_dir).as_posix()
        for path in sorted(bundle_dir.rglob("*"))
        if path.is_file()
    ]
    _ = manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_secret_check(
    tmp_path: Path,
    env_file: Path,
    *,
    warp_listener: str = "",
    docker_ps_output: str = "",
) -> subprocess.CompletedProcess[str]:
    installer = tmp_path / "install.sh"
    _ = shutil.copy2(INSTALLER, installer)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    docker = bin_dir / "docker"
    _ = docker.write_text(
        f"""#!/bin/sh
case "${{1:-}}" in
    ps)
        printf '%s' '{docker_ps_output}'
        ;;
    *)
        exit 1
        ;;
esac
""",
        encoding="utf-8",
    )
    _ = docker.chmod(0o755)
    warp_cli = bin_dir / "warp-cli"
    _ = warp_cli.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    _ = warp_cli.chmod(0o755)
    ss = bin_dir / "ss"
    _ = ss.write_text(f"#!/bin/sh\nprintf '%s' '{warp_listener}'\n", encoding="utf-8")
    _ = ss.chmod(0o755)

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
    # Given: an existing deployment whose environment file holds every previously required
    # secret but no Redis password.
    env_file = tmp_path / ".env"
    original = "\n".join(f'{key}="{value}"' for key, value in sorted(PRE_REDIS_REQUIRED_SECRETS.items())) + "\n"
    _ = env_file.write_text(original, encoding="utf-8")

    # When: bootstrap secret validation runs against that file.
    result = run_secret_check(tmp_path, env_file, docker_ps_output="existing-container")

    # Then: installation is blocked and the missing Redis password is named.
    assert result.returncode != 0, result.stdout + result.stderr
    assert "REDIS_PASSWORD" in result.stdout + result.stderr


def test_collector_auth_token_is_a_required_secret(tmp_path: Path) -> None:
    # Given: an existing deployment whose environment file holds every other required
    # secret but no collector token.
    env_file = tmp_path / ".env"
    original = "\n".join(f'{key}="{value}"' for key, value in sorted(REQUIRED_SECRETS_WITHOUT_COLLECTOR.items())) + "\n"
    _ = env_file.write_text(original, encoding="utf-8")

    # When: bootstrap secret validation runs against that file.
    result = run_secret_check(tmp_path, env_file, docker_ps_output="existing-container")

    # Then: installation is blocked and the missing collector token is named.
    assert result.returncode != 0, result.stdout + result.stderr
    assert "COLLECTOR_AUTH_TOKEN" in result.stdout + result.stderr


@pytest.mark.parametrize("missing_key", ["ADMIN_USERNAME", "ADMIN_PASSWORD"])
def test_admin_credentials_are_required_secrets(tmp_path: Path, missing_key: str) -> None:
    env_file = tmp_path / ".env"
    body = "\n".join(f'{key}="{value}"' for key, value in sorted(REQUIRED_SECRETS.items()) if key != missing_key)
    _ = env_file.write_text(body + "\n", encoding="utf-8")

    result = run_secret_check(tmp_path, env_file, docker_ps_output="existing-container")

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


def test_shared_secret_file_is_owner_readable_only() -> None:
    # Given: the init-container secret writer used by Compose.
    source = INIT_SECRETS.read_text(encoding="utf-8")

    # When: its final permission contract is inspected.
    # Then: group and other containers cannot read the generated values.
    assert "umask 077" in source
    assert 'chmod 600 "$SECRETS_FILE"' in source
    assert 'chmod 644 "$SECRETS_FILE"' not in source


def test_warp_is_disabled_when_proxy_is_not_bridge_reachable(tmp_path: Path) -> None:
    env_file = tmp_path / "etc" / "blacklist" / ".env"

    result = run_secret_check(
        tmp_path,
        env_file,
        warp_listener="LISTEN 0 1024 127.0.0.1:40000 0.0.0.0:*\n",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    generated_values = parse_env(env_file)
    assert generated_values["WARP_ENABLED"] == "false"
    assert generated_values["WARP_PROXY_URL"] == ""


def test_production_warp_stays_disabled_when_proxy_is_bridge_reachable(tmp_path: Path) -> None:
    env_file = tmp_path / "etc" / "blacklist" / ".env"

    result = run_secret_check(
        tmp_path,
        env_file,
        warp_listener="LISTEN 0 1024 0.0.0.0:40000 0.0.0.0:*\n",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    generated_values = parse_env(env_file)
    assert generated_values["WARP_ENABLED"] == "false"
    assert generated_values["WARP_PROXY_URL"] == ""


@pytest.mark.parametrize(
    "updates",
    (
        {"POSTGRES_USER": "blacklist_app", "APP_DB_USER": "blacklist_app"},
        {"POSTGRES_USER": "blacklist_collector", "COLLECTOR_DB_USER": "blacklist_collector"},
        {"APP_DB_USER": "blacklist_runtime", "COLLECTOR_DB_USER": "blacklist_runtime"},
    ),
)
def test_installer_rejects_database_role_name_collisions(tmp_path: Path, updates: dict[str, str]) -> None:
    env_file = tmp_path / "etc" / "blacklist" / ".env"
    env_file.parent.mkdir(parents=True)
    values = {
        **REQUIRED_SECRETS,
        "DB_OWNER_ROLE": "blacklist_owner",
        "APP_DB_USER": "blacklist_app",
        "APP_DB_PASSWORD": "local-app-db-password",
        "COLLECTOR_DB_USER": "blacklist_collector",
        "COLLECTOR_DB_PASSWORD": "local-collector-db-password",
        **updates,
    }
    _ = env_file.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n", encoding="utf-8")

    result = run_secret_check(tmp_path, env_file)

    assert result.returncode != 0
    assert "must be unique" in result.stdout + result.stderr


OPERATOR_ADMIN_PASSWORD = "operator-chosen-admin-password"


def write_env(tmp_path: Path, body: str) -> Path:
    env_file = tmp_path / "etc" / "blacklist" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    _ = env_file.write_text(body, encoding="utf-8")
    return env_file


def test_fresh_install_keeps_operator_values_and_generates_the_rest(tmp_path: Path) -> None:
    # Given: before the first install the operator writes only the values they choose.
    env_file = write_env(
        tmp_path,
        f"ADMIN_PASSWORD={OPERATOR_ADMIN_PASSWORD}\nWARP_ENABLED=true\nFRONTEND_BIND_ADDRESS=192.0.2.10\n",
    )

    # When: secret setup runs on a host without deployment state.
    result = run_secret_check(tmp_path, env_file)

    # Then: the chosen values survive, every other secret is generated, and the password is never echoed.
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    values = parse_env(env_file)
    assert values["ADMIN_PASSWORD"] == OPERATOR_ADMIN_PASSWORD
    assert values["ADMIN_USERNAME"] == "admin"
    assert values["WARP_ENABLED"] == "true"
    assert values["FRONTEND_BIND_ADDRESS"] == "192.0.2.10"
    assert values["COMPOSE_PROJECT_NAME"] == "blacklist"
    assert all(values[key] for key in REQUIRED_SECRETS)
    assert OPERATOR_ADMIN_PASSWORD not in output
    assert not Path(f"{env_file}.initial-admin-password").exists()
    assert os.stat(env_file).st_mode & 0o777 == 0o600


def test_fresh_install_generates_an_admin_password_left_blank(tmp_path: Path) -> None:
    # Given: the operator kept the template's empty ADMIN_PASSWORD line.
    env_file = write_env(tmp_path, "ADMIN_PASSWORD=\nWARP_ENABLED=false\n")

    result = run_secret_check(tmp_path, env_file)

    # Then: one generated password replaces the blank line and lands in the protected file.
    assert result.returncode == 0, result.stdout + result.stderr
    password = parse_env(env_file)["ADMIN_PASSWORD"]
    assert re.fullmatch(r"[0-9a-f]{64}", password)
    lines = env_file.read_text(encoding="utf-8").splitlines()
    assert sum(line.startswith("ADMIN_PASSWORD=") for line in lines) == 1
    assert Path(f"{env_file}.initial-admin-password").read_text(encoding="utf-8").strip() == password


@pytest.mark.parametrize("password", ["eleven-char", "가나다라마바사아자차카", "x" * 73])
def test_fresh_install_rejects_an_admin_password_the_app_cannot_bootstrap(tmp_path: Path, password: str) -> None:
    # Given: an operator password outside the app's 12-character / 72-byte policy.
    original = f"ADMIN_PASSWORD={password}\n"
    env_file = write_env(tmp_path, original)

    result = run_secret_check(tmp_path, env_file)

    # Then: installation stops before touching the file and never echoes the value.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "ADMIN_PASSWORD" in output
    assert password not in output
    assert env_file.read_text(encoding="utf-8") == original


def test_partial_env_is_not_completed_on_an_existing_deployment(tmp_path: Path) -> None:
    # Given: deployment state exists, so new secrets would orphan the encrypted data.
    original = f"ADMIN_PASSWORD={OPERATOR_ADMIN_PASSWORD}\n"
    env_file = write_env(tmp_path, original)

    result = run_secret_check(tmp_path, env_file, docker_ps_output="existing-container")

    # Then: the missing secrets are named and nothing is generated.
    assert result.returncode != 0
    assert "REDIS_PASSWORD" in result.stdout + result.stderr
    assert env_file.read_text(encoding="utf-8") == original


def test_operator_warp_switch_survives_repeated_secret_setup(tmp_path: Path) -> None:
    # Given: an installed env file where the operator switched WARP on with an explicit proxy.
    env_file = write_env(
        tmp_path,
        "\n".join(f"{key}={value}" for key, value in REQUIRED_SECRETS.items())
        + "\nWARP_ENABLED=true\nWARP_PROXY_URL=socks5h://172.17.0.1:40000\n",
    )

    # When: the installer runs again, as it does on every upgrade.
    first = run_secret_check(tmp_path, env_file)
    second = run_secret_check(tmp_path, env_file)

    # Then: the switch and proxy are kept instead of being reset to the disabled defaults.
    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    values = parse_env(env_file)
    assert values["WARP_ENABLED"] == "true"
    assert values["WARP_PROXY_URL"] == "socks5h://172.17.0.1:40000"
    assert "Collector WARP proxy enabled" in second.stdout


def test_missing_warp_settings_default_to_disabled(tmp_path: Path) -> None:
    env_file = write_env(tmp_path, "\n".join(f"{key}={value}" for key, value in REQUIRED_SECRETS.items()) + "\n")

    result = run_secret_check(tmp_path, env_file)

    assert result.returncode == 0, result.stdout + result.stderr
    values = parse_env(env_file)
    assert values["WARP_ENABLED"] == "false"
    assert values["WARP_PROXY_URL"] == ""


@pytest.mark.parametrize(
    ("key", "value"),
    (
        ("WARP_ENABLED", "maybe"),
        ("WARP_PROXY_URL", "ftp://172.17.0.1:40000"),
        ("WARP_PROXY_URL", "http://user:secret@172.17.0.1:40000"),
    ),
)
def test_installer_rejects_warp_values_the_collector_would_misread(tmp_path: Path, key: str, value: str) -> None:
    env_file = write_env(
        tmp_path,
        "\n".join(f"{name}={secret}" for name, secret in REQUIRED_SECRETS.items()) + f"\n{key}={value}\n",
    )

    result = run_secret_check(tmp_path, env_file)

    assert result.returncode != 0
    assert key in result.stdout + result.stderr
    assert "secret@" not in result.stdout + result.stderr


def test_regtech_login_from_the_env_file_is_kept(tmp_path: Path) -> None:
    # Given: the operator puts the REGTECH login next to the admin login before installing.
    env_file = write_env(
        tmp_path,
        "\n".join(f"{key}={value}" for key, value in REQUIRED_SECRETS.items())
        + "\nREGTECH_ID=regtech-user\nREGTECH_PW=regtech-password\n",
    )

    result = run_secret_check(tmp_path, env_file)

    # Then: both values survive for the app's first start and the password is never echoed.
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    values = parse_env(env_file)
    assert values["REGTECH_ID"] == "regtech-user"
    assert values["REGTECH_PW"] == "regtech-password"
    assert "regtech-password" not in output


@pytest.mark.parametrize("line", ["REGTECH_ID=regtech-user", "REGTECH_PW=regtech-password"])
def test_installer_rejects_half_a_regtech_login(tmp_path: Path, line: str) -> None:
    env_file = write_env(
        tmp_path,
        "\n".join(f"{key}={value}" for key, value in REQUIRED_SECRETS.items()) + f"\n{line}\n",
    )

    result = run_secret_check(tmp_path, env_file)

    assert result.returncode != 0
    assert "REGTECH_ID and REGTECH_PW" in result.stdout + result.stderr
