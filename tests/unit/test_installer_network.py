from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from .installer_network_fixtures import INSTALLER, assert_read_only, network_environment, run_network


def test_network_helper_preserves_legacy_host_python_syntax() -> None:
    source = INSTALLER.read_text(encoding="utf-8").split("readonly NETWORK_PREFLIGHT_PY='\n", 1)[1].split("\n'\n", 1)[0]

    ast.parse(source, feature_version=(3, 6))


@pytest.mark.parametrize("answers", ("0\n", "1\n0\n", "1\n1\nn\n", "", "99\nq\n"))
def test_network_wizard_cancellation_preserves_existing_configuration(tmp_path: Path, answers: str) -> None:
    environment = network_environment(tmp_path)
    env_file = Path(environment["BLACKLIST_ENV_FILE"])
    original = b"# Existing operator settings\nWARP_ENABLED=false\n"
    _ = env_file.write_bytes(original)
    env_file.chmod(0o640)

    result = run_network(environment, "--pre-scan", "--configure-network", input_text=answers)

    assert result.returncode == 130, result.stdout + result.stderr
    assert env_file.read_bytes() == original
    assert env_file.stat().st_mode & 0o777 == 0o640
    assert_read_only(environment)


@pytest.mark.parametrize(
    ("original", "answers", "expected"),
    (
        ("", "2\n1\ny\n", "198.51.100.10"),
        ("", "1\n3\ny\n", "fd00:1::10"),
        ("", "4\ny\n", "0.0.0.0"),
        ("FRONTEND_BIND_ADDRESS=192.0.2.11\n", "1\ny\n", "192.0.2.11"),
        ("FRONTEND_TLS_MODE=self-signed\n", "1\ny\n", "127.0.0.1"),
    ),
)
def test_network_wizard_previews_only_the_selected_binding(
    tmp_path: Path, original: str, answers: str, expected: str
) -> None:
    environment = network_environment(tmp_path)
    env_file = Path(environment["BLACKLIST_ENV_FILE"])
    if original:
        _ = env_file.write_text(original, encoding="utf-8")

    result = run_network(environment, "--pre-scan", "--configure-network", input_text=answers)

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"FRONTEND_BIND_ADDRESS={expected}" in result.stdout
    assert env_file.read_text(encoding="utf-8") == original if original else not env_file.exists()
    assert_read_only(environment)


@pytest.mark.parametrize(
    "arguments",
    (
        ("--interface", "missing"),
        ("--interface", "eth-down"),
        ("--bind-address", "203.0.113.99"),
        ("--interface", "eth-b", "--bind-address", "192.0.2.10"),
        ("--interface", "eth-a", "--bind-address", "fe80::10"),
    ),
)
def test_unavailable_interface_or_address_fails_without_changes(tmp_path: Path, arguments: tuple[str, ...]) -> None:
    environment = network_environment(tmp_path)

    result = run_network(environment, "--pre-scan", *arguments)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Unknown option" not in result.stdout + result.stderr
    assert not Path(environment["BLACKLIST_ENV_FILE"]).exists()
    assert_read_only(environment)


def test_unattended_interface_with_multiple_addresses_requires_an_explicit_address(tmp_path: Path) -> None:
    environment = network_environment(tmp_path)

    result = run_network(environment, "--pre-scan", "--interface", "eth-a")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "--bind-address" in result.stdout + result.stderr
    assert_read_only(environment)


@pytest.mark.parametrize("address", ("192.0.2.10", "fd00:1::10"))
def test_assigned_ipv4_and_ipv6_bindings_pass_the_read_only_scan(tmp_path: Path, address: str) -> None:
    environment = network_environment(tmp_path)

    result = run_network(environment, "--pre-scan", "--interface", "eth-a", "--bind-address", address)

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"FRONTEND_BIND_ADDRESS={address}" in result.stdout
    assert_read_only(environment)


@pytest.mark.parametrize(
    ("listener", "expected_exit"),
    (
        ("198.51.100.10:443", 0),
        ("192.0.2.10:443", 1),
        ("0.0.0.0:443", 1),
        ("[::]:443", 1),
    ),
)
def test_port_scan_checks_the_selected_bind_address(tmp_path: Path, listener: str, expected_exit: int) -> None:
    environment = network_environment(tmp_path)
    environment["TEST_LISTENERS"] = f'LISTEN 0 128 {listener} 0.0.0.0:* users:(("nginx",pid=123,fd=4))\n'

    result = run_network(environment, "--pre-scan", "--bind-address", "192.0.2.10")

    assert result.returncode == expected_exit, result.stdout + result.stderr
    if expected_exit:
        assert "443" in result.stdout + result.stderr
    assert_read_only(environment)


@pytest.mark.parametrize("owner", ("blacklist", "other-project"))
def test_existing_frontend_publication_is_reused_only_for_this_project(tmp_path: Path, owner: str) -> None:
    environment = network_environment(tmp_path)
    environment["TEST_CONTAINERS"] = json.dumps(
        [
            {
                "Id": "frontend-id",
                "Name": "/blacklist-frontend",
                "Config": {
                    "Labels": {
                        "com.docker.compose.project": owner,
                        "com.docker.compose.service": "blacklist-frontend",
                    }
                },
                "NetworkSettings": {"Ports": {"3000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "443"}]}},
            }
        ]
    )
    environment["TEST_LISTENERS"] = 'LISTEN 0 128 0.0.0.0:443 0.0.0.0:* users:(("docker-proxy",pid=123,fd=4))\n'

    result = run_network(environment, "--pre-scan", "--bind-address", "192.0.2.10")

    assert result.returncode == (0 if owner == "blacklist" else 1), result.stdout + result.stderr
    assert_read_only(environment)


@pytest.mark.parametrize(("published_ip", "expected_exit"), (("192.0.2.10", 1), ("198.51.100.10", 0)))
def test_docker_publication_is_checked_even_without_a_host_socket(
    tmp_path: Path, published_ip: str, expected_exit: int
) -> None:
    environment = network_environment(tmp_path)
    environment["TEST_CONTAINERS"] = json.dumps(
        [
            {
                "Id": "other-id",
                "Name": "/other",
                "Config": {"Labels": {}},
                "NetworkSettings": {"Ports": {"443/tcp": [{"HostIp": published_ip, "HostPort": "443"}]}},
            }
        ]
    )

    result = run_network(environment, "--pre-scan", "--bind-address", "192.0.2.10")

    assert result.returncode == expected_exit, result.stdout + result.stderr
    if expected_exit:
        assert "443" in result.stdout + result.stderr
    assert_read_only(environment)


@pytest.mark.parametrize(("owner", "subnet"), (("other", "172.30.0.0/24"), ("blacklist", "172.31.240.0/24")))
def test_conflicting_docker_subnet_is_rejected_without_reconfiguring_bridges(
    tmp_path: Path, owner: str, subnet: str
) -> None:
    environment = network_environment(tmp_path)
    environment["TEST_NETWORKS"] = json.dumps(
        [
            {
                "Id": "bridge-id",
                "Name": "existing-bridge",
                "Labels": {"com.docker.compose.project": owner, "com.docker.compose.network": "blacklist-net"},
                "Options": {},
                "IPAM": {"Config": [{"Subnet": subnet}]},
            }
        ]
    )

    result = run_network(environment, "--pre-scan", "--bind-address", "192.0.2.10")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "existing-bridge" in result.stdout + result.stderr
    assert_read_only(environment)


@pytest.mark.parametrize("own_bridge", (False, True))
def test_scan_rejects_host_route_overlap_but_preserves_the_existing_project_bridge(
    tmp_path: Path, own_bridge: bool
) -> None:
    environment = network_environment(tmp_path)
    environment["TEST_ROUTES"] = '[{"dst":"172.30.0.0/24","dev":"br-project"}]'
    if own_bridge:
        environment["TEST_NETWORKS"] = json.dumps(
            [
                {
                    "Id": "project-id",
                    "Name": "blacklist_blacklist-net",
                    "Labels": {
                        "com.docker.compose.project": "blacklist",
                        "com.docker.compose.network": "blacklist-net",
                    },
                    "Options": {"com.docker.network.bridge.name": "br-project"},
                    "IPAM": {"Config": [{"Subnet": "172.30.0.0/24"}]},
                }
            ]
        )

    result = run_network(environment, "--pre-scan", "--bind-address", "192.0.2.10")

    assert result.returncode == (0 if own_bridge else 1), result.stdout + result.stderr
    assert_read_only(environment)


@pytest.mark.parametrize("frontend_ip", ("172.30.0.10", "172.31.240.10"))
def test_inconsistent_internal_network_settings_fail_before_mutation(tmp_path: Path, frontend_ip: str) -> None:
    environment = network_environment(tmp_path)
    env_file = Path(environment["BLACKLIST_ENV_FILE"])
    original = (
        "BLACKLIST_NETWORK_SUBNET=172.31.240.0/24\n"
        f"FRONTEND_INTERNAL_IP={frontend_ip}\n"
        "TRUSTED_PROXY_NETWORKS=172.30.0.10/32\n"
    )
    _ = env_file.write_text(original, encoding="utf-8")

    result = run_network(environment, "--pre-scan", "--bind-address", "192.0.2.10")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Unknown option" not in result.stdout + result.stderr
    assert env_file.read_text(encoding="utf-8") == original
    assert_read_only(environment)


@pytest.mark.parametrize(
    ("gateway", "frontend_ip", "expected_exit"),
    (("", "172.30.0.1", 1), ("172.30.0.254", "172.30.0.254", 1), ("172.30.0.254", "172.30.0.1", 0)),
)
def test_frontend_address_does_not_use_the_new_or_existing_bridge_gateway(
    tmp_path: Path, gateway: str, frontend_ip: str, expected_exit: int
) -> None:
    environment = network_environment(tmp_path)
    if gateway:
        environment["TEST_NETWORKS"] = json.dumps(
            [
                {
                    "Id": "project-id",
                    "Name": "blacklist_blacklist-net",
                    "Labels": {
                        "com.docker.compose.project": "blacklist",
                        "com.docker.compose.network": "blacklist-net",
                    },
                    "Options": {},
                    "IPAM": {"Config": [{"Subnet": "172.30.0.0/24", "Gateway": gateway}]},
                }
            ]
        )
    env_file = Path(environment["BLACKLIST_ENV_FILE"])
    original = f"FRONTEND_INTERNAL_IP={frontend_ip}\nTRUSTED_PROXY_NETWORKS={frontend_ip}/32\n"
    _ = env_file.write_text(original, encoding="utf-8")

    result = run_network(environment, "--pre-scan", "--bind-address", "192.0.2.10")

    assert result.returncode == expected_exit, result.stdout + result.stderr
    assert env_file.read_text(encoding="utf-8") == original
    assert_read_only(environment)


def test_deployment_leaves_existing_containers_for_compose_to_reconcile(tmp_path: Path) -> None:
    environment = network_environment(tmp_path)
    environment["TEST_CONTAINERS"] = '[{"Id":"existing-container"}]'
    installer = Path(environment["TEST_INSTALLER"])
    _ = installer.write_text(
        INSTALLER.read_text(encoding="utf-8").replace('\nmain "$@"\n', "\ndeploy_services\n"),
        encoding="utf-8",
    )

    result = run_network(environment)

    assert result.returncode == 0, result.stdout + result.stderr
    calls = Path(environment["TEST_NETWORK_LOG"]).read_text(encoding="utf-8")
    assert " up -d --pull never blacklist-postgres" in calls
    assert "docker rm " not in calls
    assert "docker stop " not in calls
