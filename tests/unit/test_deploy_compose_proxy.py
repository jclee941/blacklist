from __future__ import annotations

import re
from pathlib import Path


DEPLOY_DIR = Path(__file__).parents[2] / "deploy"
DEV_OVERLAY = DEPLOY_DIR / "docker-compose.yml"
RELEASE_OVERLAY = DEPLOY_DIR / "docker-compose.release.yml"


def test_dev_proxy_is_not_container_loopback() -> None:
    # Given the dev overlay routes REGTECH traffic through a host-side WARP proxy
    overlay = DEV_OVERLAY.read_text(encoding="utf-8")
    # When the services run on a bridge network instead of the host network
    # Then 127.0.0.1 must not be used: inside a bridge container it is the
    # container's own loopback, so the host proxy becomes unreachable.
    assert "WARP_PROXY_URL" in overlay
    assert "127.0.0.1:40000" not in overlay


def test_dev_proxy_targets_the_host_gateway() -> None:
    # Given the proxy runs on the developer's host, outside the bridge network
    overlay = DEV_OVERLAY.read_text(encoding="utf-8")
    # Then the collector must reach it via the host gateway alias, which
    # requires an explicit extra_hosts mapping on Linux.
    assert "host.docker.internal" in overlay
    assert re.search(r"extra_hosts:\s*\n\s*-\s*\"?host\.docker\.internal:host-gateway", overlay)


def test_dev_proxy_can_be_disabled_by_an_empty_value() -> None:
    # Given not every developer runs the WARP proxy
    overlay = DEV_OVERLAY.read_text(encoding="utf-8")
    # Then an explicitly empty WARP_PROXY_URL must disable the proxy, so the
    # dash form (unset-only default) is required rather than :- (empty-or-unset).
    assert re.search(r"WARP_PROXY_URL:\s*\$\{WARP_PROXY_URL-", overlay)


def test_release_overlay_ships_no_proxy() -> None:
    # Given production egress is not IP-blocked, the shipped offline bundle
    # must not carry a developer-only proxy setting.
    assert "WARP_PROXY_URL" not in RELEASE_OVERLAY.read_text(encoding="utf-8")
