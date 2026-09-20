from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import TypedDict, cast

import pytest


PROJECT_ROOT = Path(__file__).parents[2]
DEVELOPMENT_COMPOSE = PROJECT_ROOT / "deploy" / "docker-compose.yml"
RELEASE_COMPOSE = PROJECT_ROOT / "deploy" / "docker-compose.release.yml"
STUB_ENV = """\
BLACKLIST_VERSION=4.1.0
POSTGRES_PASSWORD=x
APP_DB_PASSWORD=x
COLLECTOR_DB_PASSWORD=x
REDIS_PASSWORD=x
SECRET_KEY=x
FLASK_SECRET_KEY=x
JWT_SECRET_KEY=x
CREDENTIAL_MASTER_KEY=x
COLLECTOR_AUTH_TOKEN=x
CREDENTIAL_ENCRYPTION_KEY=x
SETTINGS_ENCRYPTION_KEY=x
ENCRYPTION_SALT=x
ADMIN_USERNAME=admin
ADMIN_PASSWORD=x
"""


class PublishedPort(TypedDict):
    published: str


class RenderedService(TypedDict, total=False):
    network_mode: str
    ports: list[PublishedPort]
    environment: dict[str, str]


class RenderedCompose(TypedDict):
    services: dict[str, RenderedService]


def _render_compose(
    tmp_path: Path,
    compose_file: Path = DEVELOPMENT_COMPOSE,
    extra_env: str = "",
) -> subprocess.CompletedProcess[str]:
    env_file = tmp_path / "compose.env"
    _ = env_file.write_text(STUB_ENV + extra_env, encoding="utf-8")
    return subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(compose_file),
            "--env-file",
            str(env_file),
            "config",
            "--format",
            "json",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is required")
def test_only_expected_ports_are_published(tmp_path: Path) -> None:
    # Given: the development deployment with all required secrets defined.
    # When: Docker Compose renders the inherited service configuration.
    result = _render_compose(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    rendered = cast(RenderedCompose, json.loads(result.stdout))

    # Then: the frontend HTTPS endpoint is the sole host-published port.
    published_ports = {
        str(port["published"])
        for service in rendered["services"].values()
        for port in service.get("ports", [])
    }
    assert published_ports == {"443"}


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is required")
def test_no_service_uses_host_network_mode(tmp_path: Path) -> None:
    # Given: the development deployment with all required secrets defined.
    # When: Docker Compose renders the inherited service configuration.
    result = _render_compose(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    rendered = cast(RenderedCompose, json.loads(result.stdout))

    # Then: no rendered service joins the host network namespace.
    assert all(service.get("network_mode") != "host" for service in rendered["services"].values())


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is required")
@pytest.mark.parametrize("compose_file", (DEVELOPMENT_COMPOSE, RELEASE_COMPOSE), ids=("development", "release"))
@pytest.mark.parametrize(
    ("configured", "expected"),
    ((None, "127.0.0.1,::1"), ("", ""), ("198.51.100.42,203.0.113.", "198.51.100.42,203.0.113.")),
    ids=("default", "disabled", "operator-override"),
)
def test_rate_limit_whitelist_reaches_app_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    compose_file: Path,
    configured: str | None,
    expected: str,
) -> None:
    monkeypatch.delenv("RATE_LIMIT_WHITELIST", raising=False)
    extra_env = "" if configured is None else f"RATE_LIMIT_WHITELIST={configured}\n"

    result = _render_compose(tmp_path, compose_file, extra_env)

    assert result.returncode == 0, result.stdout + result.stderr
    rendered = cast(RenderedCompose, json.loads(result.stdout))
    assert rendered["services"]["blacklist-app"].get("environment", {}).get("RATE_LIMIT_WHITELIST") == expected
