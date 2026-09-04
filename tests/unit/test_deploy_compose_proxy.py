import re
from pathlib import Path


DEPLOY_DIR = Path(__file__).parents[2] / "deploy"
BASE_COMPOSE = DEPLOY_DIR / "base.yml"
DEV_OVERLAY = DEPLOY_DIR / "docker-compose.yml"
RELEASE_OVERLAY = DEPLOY_DIR / "docker-compose.release.yml"


def test_dev_proxy_is_not_container_loopback() -> None:
    # Given the dev overlay routes REGTECH traffic through a host-side WARP proxy
    overlay = DEV_OVERLAY.read_text(encoding="utf-8")
    # When the services run on a bridge network instead of the host network
    # Then 127.0.0.1 must not be used: inside a bridge container it is the
    # container's own loopback, so the host proxy becomes unreachable.
    assert "127.0.0.1:40000" not in overlay


def test_dev_proxy_targets_the_host_gateway() -> None:
    # Given the proxy runs on the developer's host, outside the bridge network
    overlay = DEV_OVERLAY.read_text(encoding="utf-8")
    # Then the collector must reach it via the host gateway alias, which
    # requires an explicit extra_hosts mapping on Linux.
    assert re.search(r"extra_hosts:\s*\n\s*-\s*\"?host\.docker\.internal:host-gateway", overlay)


def test_shared_proxy_defaults_to_disabled() -> None:
    base = BASE_COMPOSE.read_text(encoding="utf-8")

    assert re.search(r'WARP_ENABLED:\s*"false"', base)
    assert re.search(r'WARP_PROXY_URL:\s*""', base)


def test_release_overlay_forces_proxy_off() -> None:
    release = RELEASE_OVERLAY.read_text(encoding="utf-8")

    assert 'WARP_ENABLED: "false"' in release
    assert 'WARP_PROXY_URL: ""' in release
