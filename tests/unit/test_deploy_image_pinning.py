from __future__ import annotations

import os
import re
from pathlib import Path


REPO_ROOT = Path(__file__).parents[2]
DEPLOY_DIR = REPO_ROOT / "deploy"
RELEASE_OVERLAY = DEPLOY_DIR / "docker-compose.release.yml"
DEVELOPMENT_COMPOSE = DEPLOY_DIR / "docker-compose.yml"
INSTALLER = DEPLOY_DIR / "install.sh"
BUILD_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "build-images.yml"

RELEASE_SERVICES = (
    "blacklist-postgres",
    "blacklist-redis",
    "blacklist-collector",
    "blacklist-app",
    "blacklist-frontend",
)


def test_release_images_are_not_floating_latest() -> None:
    # Given: the bundle ships images saved as blacklist-<service>:<version>,
    # and the installer no longer retags them to :latest.
    overlay = RELEASE_OVERLAY.read_text(encoding="utf-8")
    # Then: a :latest reference would point at an image that does not exist on
    # the target host, so the deployment would fail to start.
    assert ":latest" not in overlay


def test_release_images_resolve_the_deployed_version() -> None:
    # Given: the installer writes BLACKLIST_VERSION into the env file it passes
    # to every docker compose invocation.
    overlay = RELEASE_OVERLAY.read_text(encoding="utf-8")
    # Then: every release service pins its image to that version.
    for service in RELEASE_SERVICES:
        assert re.search(
            rf"image:\s*{re.escape(service)}:\$\{{BLACKLIST_VERSION",
            overlay,
        ), service


def test_unset_version_fails_loudly() -> None:
    # Given: an unset variable must not silently resolve to an empty tag.
    overlay = RELEASE_OVERLAY.read_text(encoding="utf-8")
    # Then: the required-variable form is used, so compose aborts with a message.
    assert overlay.count("${BLACKLIST_VERSION:?") == len(RELEASE_SERVICES)


def test_installer_exports_the_version_it_loaded() -> None:
    # Given: the compose files above consume BLACKLIST_VERSION.
    installer = INSTALLER.read_text(encoding="utf-8")
    # Then: the installer must write it into the generated environment file.
    assert "BLACKLIST_VERSION=${VERSION}" in installer


def test_source_installer_resolves_the_repository_version() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")

    assert '${SCRIPT_DIR}/../VERSION' in installer


def test_development_builds_receive_the_declared_version() -> None:
    compose = DEVELOPMENT_COMPOSE.read_text(encoding="utf-8")

    assert compose.count("APP_VERSION: ${BLACKLIST_VERSION:-0.0.0-dev}") == len(RELEASE_SERVICES)


def test_bundle_images_carry_the_version_tag() -> None:
    # Given: this pinning is only correct if the saved images really are tagged
    # with the version rather than latest.
    workflow = BUILD_WORKFLOW.read_text(encoding="utf-8")
    # Then: the packaging step saves them under the version tag.
    assert re.search(
        r"docker save blacklist-\$\{\{ matrix\.service \}\}:\$\{\{ inputs\.version \}\}",
        workflow,
    )


def test_upgrade_refreshes_the_deployment_version(tmp_path: Path) -> None:
    # Given: an env file left behind by an OLDER install. setup_secrets() never
    # rewrites an existing file, so a stale BLACKLIST_VERSION would make compose
    # resolve the previous image tag and silently redeploy the old release.
    import subprocess

    installer = tmp_path / "install.sh"
    _ = installer.write_bytes(INSTALLER.read_bytes())
    # The shipped bundle carries a VERSION file next to install.sh; the installer
    # resolves its own VERSION from it.
    _ = (tmp_path / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    env_file = tmp_path / "etc" / ".env"
    env_file.parent.mkdir(parents=True)
    secrets = (
        "CREDENTIAL_MASTER_KEY=local-credential-master-key-0123456789",
        "SECRET_KEY=local-secret-key-0123456789",
        "FLASK_SECRET_KEY=local-flask-secret-key-0123456789",
        "JWT_SECRET_KEY=local-jwt-secret-key-0123456789",
        "CREDENTIAL_ENCRYPTION_KEY=local-credential-encryption-key-0123456789",
        "SETTINGS_ENCRYPTION_KEY=local-settings-encryption-key-0123456789",
        "ENCRYPTION_SALT=local-encryption-salt-0123456789",
        "POSTGRES_PASSWORD=local-postgres-password-0123456789",
        "REDIS_PASSWORD=local-redis-password-0123456789",
        "COLLECTOR_AUTH_TOKEN=local-collector-auth-token-0123456789",
        "ADMIN_USERNAME=admin",
        "ADMIN_PASSWORD=local-admin-password-0123456789",
        "BLACKLIST_VERSION=0.0.1-stale",
    )
    _ = env_file.write_text("\n".join(secrets) + "\n", encoding="utf-8")
    env_file.chmod(0o600)

    # When: the newer installer validates the existing secrets.
    environment = dict(os.environ, BLACKLIST_ENV_FILE=str(env_file))
    result = subprocess.run(
        ["bash", str(installer), "--check-secrets"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    # Then: the version tracks the installer, every secret is preserved verbatim,
    # and the file stays private.
    body = env_file.read_text(encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "BLACKLIST_VERSION=9.9.9" in body
    assert "0.0.1-stale" not in body
    for secret in secrets[:-1]:
        assert secret in body
    assert os.stat(env_file).st_mode & 0o777 == 0o600
