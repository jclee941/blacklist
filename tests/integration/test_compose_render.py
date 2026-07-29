from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import TypedDict, cast

import pytest


PROJECT_ROOT = Path(__file__).parents[2]
BASE_COMPOSE = PROJECT_ROOT / "deploy" / "base.yml"
DEVELOPMENT_COMPOSE = PROJECT_ROOT / "deploy" / "docker-compose.yml"
STUB_ENV = """\
BLACKLIST_VERSION=4.1.0
POSTGRES_PASSWORD=x
REDIS_PASSWORD=x
SECRET_KEY=x
CREDENTIAL_MASTER_KEY=x
CREDENTIAL_ENCRYPTION_KEY=x
ENCRYPTION_SALT=x
ADMIN_USERNAME=admin
ADMIN_PASSWORD=x
"""


class PublishedPort(TypedDict):
    published: str


class RenderedService(TypedDict, total=False):
    network_mode: str
    ports: list[PublishedPort]


class RenderedCompose(TypedDict):
    services: dict[str, RenderedService]


def _render_compose(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env_file = tmp_path / "compose.env"
    _ = env_file.write_text(STUB_ENV, encoding="utf-8")
    return subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(BASE_COMPOSE),
            "-f",
            str(DEVELOPMENT_COMPOSE),
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
