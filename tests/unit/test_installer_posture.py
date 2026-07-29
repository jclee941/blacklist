from __future__ import annotations

import gzip
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest


DEPLOY_DIR = Path(__file__).parents[2] / "deploy"
INSTALLER = DEPLOY_DIR / "install.sh"
BUNDLE_IMAGES = (
    "blacklist-app.tar.gz",
    "blacklist-collector.tar.gz",
    "blacklist-frontend.tar.gz",
    "blacklist-postgres.tar.gz",
    "blacklist-redis.tar.gz",
)
STUB_SECRETS = {
    "COMPOSE_PROJECT_NAME": "blacklist",
    "CREDENTIAL_MASTER_KEY": "local-credential-master-key-0123456789",
    "SECRET_KEY": "local-secret-key-0123456789",
    "CREDENTIAL_ENCRYPTION_KEY": "local-credential-encryption-key-0123456789",
    "ENCRYPTION_SALT": "local-encryption-salt-0123456789",
    "POSTGRES_PASSWORD": "local-postgres-password-0123456789",
    "REDIS_PASSWORD": "local-redis-password-0123456789",
}
HOST_NETWORK_COMPOSE = """services:
  blacklist-collector:
    image: blacklist-collector:latest
    network_mode: host
"""
PASSWORDLESS_REDIS_COMPOSE = """services:
  blacklist-redis:
    image: blacklist-redis:latest
    command:
      - redis-server
      - --bind
      - 0.0.0.0
"""
UNSET_REDIS_PASSWORD_COMPOSE = """services:
  blacklist-redis:
    image: blacklist-redis:latest
    command:
      - redis-server
      - --requirepass
      - ${REDIS_PASSWORD}
"""
JWT_ADR_DRIFT_COMPOSE = """services:
  blacklist-collector:
    image: blacklist-collector:latest
    environment:
      DISABLE_JWT_AUTH: "true"
"""


def compose_with_published_port(service: str, port: str) -> str:
    lines = [
        "services:",
        f"  {service}:",
        f"    image: {service}:latest",
        "    ports:",
        f'      - "{port}:{port}"',
    ]
    if service == "blacklist-redis":
        # Keep the Redis password invariant satisfied so only the published port is violated.
        lines += [
            "    command:",
            "      - redis-server",
            "      - --requirepass",
            "      - local-redis-password-0123456789",
        ]
    return "\n".join(lines) + "\n"


def write_env_file(tmp_path: Path, omitted_keys: tuple[str, ...]) -> Path:
    env_file = tmp_path / "etc" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(
        f"{key}={value}" for key, value in STUB_SECRETS.items() if key not in omitted_keys
    )
    _ = env_file.write_text(body + "\n", encoding="utf-8")
    return env_file


def prepare_bundle(
    tmp_path: Path,
    compose_text: str,
    omitted_keys: tuple[str, ...] = (),
) -> dict[str, str]:
    installer = tmp_path / "install.sh"
    _ = shutil.copy2(INSTALLER, installer)

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    # Mirror the shipped 4.1.0 bundle: blacklist-prefixed names plus a bare-filename
    # checksums.sha256, which the fail-closed integrity check now requires.
    checksum_lines: list[str] = []
    for image_name in BUNDLE_IMAGES:
        payload = gzip.compress(b"fake-image-archive")
        _ = (images_dir / image_name).write_bytes(payload)
        checksum_lines.append(f"{hashlib.sha256(payload).hexdigest()}  {image_name}")
    _ = (images_dir / "checksums.sha256").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )

    _ = (tmp_path / "docker-compose.yml").write_text(compose_text, encoding="utf-8")

    environment = os.environ.copy()
    environment["BLACKLIST_ENV_FILE"] = str(write_env_file(tmp_path, omitted_keys))
    return environment


def prepare_released_bundle(tmp_path: Path) -> dict[str, str]:
    compose_text = (DEPLOY_DIR / "docker-compose.yml").read_text(encoding="utf-8")
    environment = prepare_bundle(tmp_path, compose_text)
    _ = shutil.copy2(DEPLOY_DIR / "base.yml", tmp_path / "base.yml")
    return environment


def write_manifest(bundle_dir: Path) -> None:
    """Regenerate MANIFEST.sha256 from the bundle's CURRENT contents.

    Manifest verification runs before the posture gate, so a scratch bundle whose
    manifest does not match would be rejected for integrity reasons and the
    posture invariant under test would never be reached.
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


def run_posture_gate(
    tmp_path: Path,
    environment: dict[str, str],
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    write_manifest(tmp_path)
    return subprocess.run(
        ["bash", str(tmp_path / "install.sh"), "--verify-only", *arguments],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )


def test_host_networking_is_rejected(tmp_path: Path) -> None:
    # Given: a hand-patched bundle that puts the collector back on the host network.
    environment = prepare_bundle(tmp_path, HOST_NETWORK_COMPOSE)

    # When: the installer verifies the effective configuration.
    result = run_posture_gate(tmp_path, environment)

    # Then: the configuration is refused and the offending service is named.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "blacklist-collector" in output, output
    assert "network_mode" in output, output


@pytest.mark.parametrize(
    ("service", "port"),
    [
        ("blacklist-postgres", "5432"),
        ("blacklist-redis", "6379"),
        ("blacklist-collector", "8545"),
    ],
)
def test_published_datastore_port_is_rejected(tmp_path: Path, service: str, port: str) -> None:
    # Given: a bundle that republishes a datastore or collector port on the host.
    environment = prepare_bundle(tmp_path, compose_with_published_port(service, port))

    # When: the installer verifies the effective configuration.
    result = run_posture_gate(tmp_path, environment)

    # Then: the configuration is refused, naming both the service and the published port.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert service in output, output
    assert port in output, output


def test_passwordless_redis_is_rejected(tmp_path: Path) -> None:
    # Given: a bundle whose Redis command drops password enforcement.
    environment = prepare_bundle(tmp_path, PASSWORDLESS_REDIS_COMPOSE)

    # When: the installer verifies the effective configuration.
    result = run_posture_gate(tmp_path, environment)

    # Then: the configuration is refused, naming Redis and the missing option.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "blacklist-redis" in output, output
    assert "--requirepass" in output, output


def test_unset_redis_password_is_rejected(tmp_path: Path) -> None:
    # Given: a bundle that asks for a Redis password the environment file never supplies.
    environment = prepare_bundle(
        tmp_path,
        UNSET_REDIS_PASSWORD_COMPOSE,
        omitted_keys=("REDIS_PASSWORD",),
    )

    # When: the installer verifies the effective configuration.
    result = run_posture_gate(tmp_path, environment)

    # Then: the empty password is refused rather than deployed.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "REDIS_PASSWORD" in output, output


def test_compliant_config_passes(tmp_path: Path) -> None:
    # Given: a bundle carrying the reviewed deploy/ Compose set unchanged.
    environment = prepare_released_bundle(tmp_path)

    # When: the installer verifies the effective configuration.
    result = run_posture_gate(tmp_path, environment)

    # Then: the gate runs and accepts the reviewed posture instead of blocking every install.
    output = result.stdout + result.stderr
    assert "security posture" in output.lower(), output
    assert result.returncode == 0, output


def test_posture_gate_runs_before_deploy() -> None:
    # Given: the installer as shipped inside the release bundle.
    installer_source = INSTALLER.read_text(encoding="utf-8")

    # When: the install order inside main() is inspected.
    main_body = installer_source.split("\nmain() {", 1)[-1]
    call_sites = [line.strip() for line in main_body.splitlines() if line.strip() == "verify_security_posture"]
    validate_index = main_body.rfind("validate_compose_config")
    posture_index = main_body.rfind("verify_security_posture")
    deploy_index = main_body.rfind("deploy_services")

    # Then: the gate guards both the read-only audit path and the install path.
    assert len(call_sites) == 2, main_body

    # Then: a violating configuration is refused before any service is started.
    assert validate_index != -1, main_body
    assert deploy_index != -1, main_body
    assert validate_index < posture_index < deploy_index, main_body



def test_skip_posture_check_is_a_loud_escape_hatch(tmp_path: Path) -> None:
    # Given: a violating bundle an operator must still deploy during an incident.
    environment = prepare_bundle(tmp_path, HOST_NETWORK_COMPOSE)

    # When: the operator opts out of the gate explicitly.
    result = run_posture_gate(tmp_path, environment, "--skip-posture-check")

    # Then: verification continues, but the skipped check is announced loudly.
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "[WARN]" in output, output
    assert "security posture check skipped" in output.lower(), output



def test_jwt_flag_flip_against_the_adr_is_rejected(tmp_path: Path) -> None:
    # Given: a bundle that disables collector auth even though ADR-0002 now records
    # Decision: enforce, i.e. the collector really does verify a bearer token.
    environment = prepare_bundle(tmp_path, JWT_ADR_DRIFT_COMPOSE)

    # When: the installer verifies the effective configuration.
    result = run_posture_gate(tmp_path, environment)

    # Then: drift from the recorded decision is refused, because silently disabling
    # enforcement would reopen the collector control API.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "blacklist-collector" in output, output
    assert "DISABLE_JWT_AUTH" in output, output
    assert "ADR-0002" in output, output
