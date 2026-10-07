import re
from pathlib import Path


DEPLOY_DIR = Path(__file__).parents[2] / "deploy"
BASE_COMPOSE = DEPLOY_DIR / "base.yml"
DEV_OVERLAY = DEPLOY_DIR / "docker-compose.yml"
RELEASE_OVERLAY = DEPLOY_DIR / "docker-compose.release.yml"


def test_collector_proxy_is_not_container_loopback() -> None:
    # Given the collector reaches a WARP proxy on the Docker host
    # When the services run on a bridge network instead of the host network
    # Then 127.0.0.1 must not be used: inside a bridge container it is the
    # container's own loopback, so the host proxy becomes unreachable.
    for compose_file in (BASE_COMPOSE, DEV_OVERLAY):
        assert "127.0.0.1:40000" not in compose_file.read_text(encoding="utf-8"), compose_file.name


def test_collector_proxy_targets_the_host_gateway() -> None:
    # Given the proxy runs on the Docker host, outside the bridge network
    base = BASE_COMPOSE.read_text(encoding="utf-8")
    # Then the default URL uses the host gateway alias, which requires an
    # explicit extra_hosts mapping on Linux.
    assert "WARP_PROXY_URL: ${WARP_PROXY_URL:-http://host.docker.internal:40000}" in base
    assert re.search(r"extra_hosts:\s*\n\s*-\s*\"?host\.docker\.internal:host-gateway", base)


def test_env_file_switch_defaults_to_disabled() -> None:
    base = BASE_COMPOSE.read_text(encoding="utf-8")

    assert "WARP_ENABLED: ${WARP_ENABLED:-false}" in base


def test_release_overlay_leaves_the_switch_to_the_env_file() -> None:
    release = RELEASE_OVERLAY.read_text(encoding="utf-8")

    assert "WARP_" not in release


def test_dev_overlay_defaults_the_switch_on() -> None:
    overlay = DEV_OVERLAY.read_text(encoding="utf-8")

    assert "WARP_ENABLED: ${WARP_ENABLED:-true}" in overlay
