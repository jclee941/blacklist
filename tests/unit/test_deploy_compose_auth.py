from __future__ import annotations

import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[2]
BASE_COMPOSE = REPOSITORY_ROOT / "deploy" / "base.yml"
ENV_EXAMPLE = REPOSITORY_ROOT / "deploy" / ".env.example"
COLLECTOR_AUTH_ADR = REPOSITORY_ROOT / "docs" / "decisions" / "0002-collector-authentication-enforcement.md"
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
    # When: its enforced authentication setting and ADR decision are inspected.
    # Then: enforcement is enabled and anchored to the governing ADR.
    adr_source = COLLECTOR_AUTH_ADR.read_text(encoding="utf-8")

    assert 'DISABLE_JWT_AUTH: "false"' in _service_block("blacklist-collector")
    assert "0002-collector-authentication-enforcement" in BASE_SOURCE
    assert re.search(r"(?m)^Decision:\s*enforce\s*$", adr_source) is not None


def test_collector_auth_secret_is_wired_to_both_services() -> None:
    collector_service = _service_block("blacklist-collector")
    app_service = _service_block("blacklist-app")

    assert "COLLECTOR_AUTH_TOKEN: ${COLLECTOR_AUTH_TOKEN:-}" in collector_service
    assert "COLLECTOR_AUTH_TOKEN: ${COLLECTOR_AUTH_TOKEN:-}" in app_service


def test_collector_auth_secret_example_is_an_empty_placeholder() -> None:
    env_example = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert re.search(r"(?m)^COLLECTOR_AUTH_TOKEN=$", env_example) is not None


def test_collection_timeout_is_wired_to_the_app_service() -> None:
    app_service = _service_block("blacklist-app")

    assert "COLLECTOR_COLLECTION_TIMEOUT: ${COLLECTOR_COLLECTION_TIMEOUT:-360}" in app_service


def test_collection_timeout_default_is_documented() -> None:
    env_example = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert re.search(r"(?m)^# COLLECTOR_COLLECTION_TIMEOUT=360\b", env_example) is not None


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


def test_admin_credentials_reach_the_app_container() -> None:
    # Given: install.sh generates ADMIN_USERNAME/ADMIN_PASSWORD on the target host.
    base = (Path(__file__).parents[2] / "deploy" / "base.yml").read_text(encoding="utf-8")
    # Then: compose must forward them, or the app never sees the generated values
    # and falls back to a login it can never satisfy.
    assert "ADMIN_USERNAME: ${ADMIN_USERNAME:?" in base
    assert "ADMIN_PASSWORD: ${ADMIN_PASSWORD:?" in base


def test_admin_credentials_are_not_hardcoded_in_compose() -> None:
    # Given: the bundle is byte-identical for every customer.
    base = (Path(__file__).parents[2] / "deploy" / "base.yml").read_text(encoding="utf-8")
    # Then: only variable references may appear, never literal values.
    for line in base.splitlines():
        stripped = line.strip()
        if stripped.startswith(("ADMIN_USERNAME:", "ADMIN_PASSWORD:")):
            assert "${" in stripped, stripped
