from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


INSTALLER = Path(__file__).parents[2] / "deploy" / "install.sh"
FAKE_NETWORK_COMMAND = """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

name = Path(sys.argv[0]).name
args = sys.argv[1:]
with Path(os.environ["TEST_NETWORK_LOG"]).open("a") as log:
    log.write(name + " " + " ".join(args) + "\\n")
match name:
    case "ip":
        if "-j" not in args or not ({"address", "route"} & set(args)):
            sys.exit(97)
        key = "TEST_LINKS" if "address" in args else "TEST_ROUTES"
        print(os.environ[key])
    case "ss":
        print(os.environ.get("TEST_LISTENERS", ""), end="")
    case "docker":
        if args[:2] == ["network", "ls"]:
            print("\\n".join(item["Id"] for item in json.loads(os.environ["TEST_NETWORKS"])))
        elif args[:2] == ["network", "inspect"]:
            print(os.environ["TEST_NETWORKS"])
        elif args[0] == "ps":
            print("\\n".join(item["Id"] for item in json.loads(os.environ["TEST_CONTAINERS"])))
        elif args[0] == "inspect":
            print("healthy" if "-f" in args else os.environ["TEST_CONTAINERS"])
        elif args[0] not in {"compose", "exec", "rm", "stop", "run"}:
            sys.exit(97)
"""


def network_environment(root: Path) -> dict[str, str]:
    bundle = root / "bundle"
    bundle.mkdir()
    _ = shutil.copy2(INSTALLER, bundle / "install.sh")
    bin_dir = root / "bin"
    bin_dir.mkdir()
    for command in ("ip", "ss", "docker"):
        executable = bin_dir / command
        _ = executable.write_text(FAKE_NETWORK_COMMAND, encoding="utf-8")
        executable.chmod(0o755)
    links = [
        {
            "ifname": name,
            "flags": ["UP"],
            "operstate": state,
            "addr_info": [{"family": "inet6" if ":" in address else "inet", "local": address} for address in addresses],
        }
        for name, state, addresses in (
            ("lo", "UNKNOWN", ("127.0.0.1",)),
            ("eth-a", "UP", ("192.0.2.10", "192.0.2.11", "fd00:1::10", "fe80::10")),
            ("eth-b", "UP", ("198.51.100.10",)),
            ("eth-down", "DOWN", ("203.0.113.10",)),
            ("docker0", "UP", ("172.17.0.1",)),
        )
    ]
    return {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "BLACKLIST_ENV_FILE": str(root / ".env"),
        "TEST_INSTALLER": str(bundle / "install.sh"),
        "TEST_NETWORK_LOG": str(root / "network.log"),
        "TEST_LINKS": json.dumps(links),
        "TEST_ROUTES": '[{"dst":"default","dev":"eth-a"},{"dst":"192.0.2.0/24","dev":"eth-a"}]',
        "TEST_NETWORKS": "[]",
        "TEST_CONTAINERS": "[]",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def run_network(environment: dict[str, str], *arguments: str, input_text: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", environment["TEST_INSTALLER"], *arguments],
        capture_output=True,
        check=False,
        env=environment,
        input=input_text,
        text=True,
    )


def assert_read_only(environment: dict[str, str]) -> None:
    calls = Path(environment["TEST_NETWORK_LOG"]).read_text(encoding="utf-8").splitlines()
    assert not [
        call for call in calls if call.startswith(("docker rm ", "docker stop ", "docker run ", "docker compose "))
    ]
    assert all(call.startswith(("ip -j ", "ss ", "docker network ", "docker ps ", "docker inspect ")) for call in calls)
