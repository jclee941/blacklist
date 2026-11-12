from __future__ import annotations

from pathlib import Path

import pytest

from . import test_installer_one_command
from .test_installer_one_command import (
    ReleaseKey,
    installer_environment,
    one_command_arguments,
    prepare_bundle,
    run_installer,
    write_certificate,
)

release_key = test_installer_one_command.release_key


@pytest.mark.parametrize("existing_environment", (False, True))
def test_install_port_conflict_preserves_services_keys_and_environment(
    tmp_path: Path, release_key: ReleaseKey, existing_environment: bool
) -> None:
    bundle = prepare_bundle(tmp_path, release_key)
    environment = installer_environment(tmp_path)
    certificate, private_key = write_certificate(tmp_path / "operator", "DNS:blacklist.example.test")
    env_file = Path(environment["BLACKLIST_ENV_FILE"])
    original = b"FRONTEND_BIND_ADDRESS=192.0.2.10\nWARP_ENABLED=false\n"
    if existing_environment:
        env_file.parent.mkdir()
        _ = env_file.write_bytes(original)
        env_file.chmod(0o640)
    ss = tmp_path / "bin" / "ss"
    _ = ss.write_text(
        '#!/bin/sh\nprintf "%s\\n" \'LISTEN 0 128 192.0.2.10:443 0.0.0.0:* users:(("nginx",pid=123,fd=4))\'\n',
        encoding="utf-8",
    )

    result = run_installer(
        bundle,
        environment,
        "--bind-address",
        "192.0.2.10",
        *one_command_arguments(release_key, certificate, private_key),
    )

    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "443 is already in use" in output
    assert not Path(environment["BLACKLIST_RELEASE_KEYRING"]).exists()
    assert not Path(environment["BLACKLIST_FRONTEND_TLS_DIR"]).exists()
    if existing_environment:
        assert env_file.read_bytes() == original
        assert env_file.stat().st_mode & 0o777 == 0o640
    else:
        assert not env_file.exists()
    calls = (tmp_path / "docker.log").read_text(encoding="utf-8").splitlines()
    assert all(call.startswith(("network ", "ps ", "inspect ")) for call in calls)
