from __future__ import annotations

import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[2]
BASE_COMPOSE = REPOSITORY_ROOT / "deploy" / "base.yml"
RELEASE_NOTES = REPOSITORY_ROOT / "docs" / "manual" / "blacklist-4.1.0-release-notes.md"
BASE_SOURCE = BASE_COMPOSE.read_text(encoding="utf-8")


def _service_block(service_name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(service_name)}:\n.*?(?=^(?:\S|  \S)|\Z)",
        BASE_SOURCE,
    )
    assert match is not None, f"service block not found: {service_name}"
    return match.group(0)


def test_collector_auth_matches_adr() -> None:
    # Given: the collector's shared Compose environment.
    # When: its deferred authentication setting is inspected.
    # Then: it remains enabled and is anchored to the governing ADR.
    assert 'DISABLE_JWT_AUTH: "true"' in BASE_SOURCE
    assert "0002-collector-authentication-enforcement" in BASE_SOURCE


def test_collector_publishes_no_ports() -> None:
    # Given: the collector service definition.
    collector_service = _service_block("blacklist-collector")

    # When: the service block is inspected.
    # Then: bridge-network isolation is not weakened by a host port mapping.
    assert re.search(r"(?m)^    ports:", collector_service) is None


def test_release_notes_have_no_false_loopback_claim() -> None:
    # Given: the current 4.1.0 release notes.
    release_notes = RELEASE_NOTES.read_text(encoding="utf-8")

    # When: the old isolation claim is checked.
    # Then: the notes don't describe the collector as container-internal loopback.
    assert "container-internal loopback" not in release_notes
