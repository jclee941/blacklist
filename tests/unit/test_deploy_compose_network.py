from __future__ import annotations

import re
from pathlib import Path


BASE_COMPOSE = Path(__file__).parents[2] / "deploy" / "base.yml"
BASE_SOURCE = BASE_COMPOSE.read_text(encoding="utf-8")


def _service_block(service_name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(service_name)}:\n.*?(?=^(?:\S|  \S)|\Z)",
        BASE_SOURCE,
    )
    assert match is not None, f"service block not found: {service_name}"
    return match.group(0)


def test_no_service_uses_host_networking() -> None:
    # Given: the shared Compose service definitions.
    # When: their network configuration is inspected.
    # Then: no service bypasses Docker networking through the host namespace.
    assert "network_mode: host" not in BASE_SOURCE


def test_bridge_network_is_declared() -> None:
    # Given: the shared Compose top-level declarations.
    # When: the network mapping is inspected.
    # Then: the deployment owns a named bridge network.
    assert re.search(
        r"(?m)^networks:\n  blacklist-net:\n    driver: bridge(?:\n|$)",
        BASE_SOURCE,
    )


def test_datastores_publish_no_ports() -> None:
    # Given: every service that must remain internal to the deployment.
    internal_services = (
        "blacklist-postgres",
        "blacklist-redis",
        "blacklist-collector",
        "blacklist-app",
    )

    # When: each two-space-indented service block is isolated.
    service_blocks = (_service_block(service_name) for service_name in internal_services)

    # Then: none of those services publishes a host port.
    assert all(re.search(r"(?m)^    ports:", block) is None for block in service_blocks)


def test_services_address_each_other_by_service_name() -> None:
    # Given: the services that communicate across the deployment network.
    collector_service = _service_block("blacklist-collector")
    app_service = _service_block("blacklist-app")
    frontend_service = _service_block("blacklist-frontend")

    # When: database, cache, collector, and API upstreams are inspected.
    # Then: every inter-service endpoint uses Docker service discovery.
    for service in (collector_service, app_service):
        assert "POSTGRES_HOST: blacklist-postgres" in service
        assert "REDIS_HOST: blacklist-redis" in service
    assert "http://blacklist-collector:8545" in app_service
    assert "http://blacklist-app:2542" in collector_service
    assert "http://blacklist-app:2542" in frontend_service

    inter_service_urls: list[str] = re.findall(
        r"(?m)^\s+[A-Z_]+_URL:\s*(\S+)",
        BASE_SOURCE,
    )
    assert all("localhost" not in url for url in inter_service_urls)
