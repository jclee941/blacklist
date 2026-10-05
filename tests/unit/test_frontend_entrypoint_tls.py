from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


ENTRYPOINT = Path(__file__).parents[2] / "frontend" / "entrypoint.sh"


def run_provided_mode(
    tmp_path: Path, subject_alt_names: str, server_name: str
) -> tuple[subprocess.CompletedProcess[str], Path]:
    certificate = tmp_path / "server.crt"
    private_key = tmp_path / "server.key"
    _ = subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "ec",
            "-pkeyopt",
            "ec_paramgen_curve:prime256v1",
            "-nodes",
            "-days",
            "2",
            "-subj",
            "/CN=frontend-test",
            "-addext",
            f"subjectAltName={subject_alt_names}",
            "-keyout",
            str(private_key),
            "-out",
            str(certificate),
        ],
        capture_output=True,
        check=True,
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    started = tmp_path / "server-started"
    node = bin_dir / "node"
    _ = node.write_text(f"#!/bin/sh\ntouch {started}\n", encoding="utf-8")
    node.chmod(0o755)
    environment = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "FRONTEND_TLS_MODE": "provided",
        "FRONTEND_TLS_SERVER_NAME": server_name,
        "SSL_CERT_PATH": str(certificate),
        "SSL_KEY_PATH": str(private_key),
    }
    result = subprocess.run(
        ["sh", str(ENTRYPOINT)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )
    return result, started


@pytest.mark.parametrize(
    ("subject_alt_names", "server_name"),
    [
        ("DNS:blacklist.example.test", "blacklist.example.test"),
        ("DNS:cafe.de", "cafe.de"),
        ("IP:10.20.30.40", "10.20.30.40"),
    ],
)
def test_certificate_covering_the_server_name_starts_the_server(
    tmp_path: Path,
    subject_alt_names: str,
    server_name: str,
) -> None:
    result, started = run_provided_mode(tmp_path, subject_alt_names, server_name)

    assert result.returncode == 0, result.stdout + result.stderr
    assert started.exists()


@pytest.mark.parametrize(
    ("subject_alt_names", "server_name"),
    [
        ("DNS:other.example.test", "blacklist.example.test"),
        ("IP:10.20.30.41", "10.20.30.40"),
    ],
)
def test_certificate_for_another_name_is_refused(
    tmp_path: Path,
    subject_alt_names: str,
    server_name: str,
) -> None:
    # Given: openssl -checkhost/-checkip exit 0 on a mismatch, so only the verdict text can refuse this.
    result, started = run_provided_mode(tmp_path, subject_alt_names, server_name)

    assert result.returncode != 0, result.stdout + result.stderr
    assert f"does not cover {server_name}" in result.stderr
    assert not started.exists()
