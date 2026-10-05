from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest


INSTALLER = Path(__file__).parents[2] / "deploy" / "install.sh"
BUNDLE_IMAGES = (
    "blacklist-app.tar.gz",
    "blacklist-collector.tar.gz",
    "blacklist-frontend.tar.gz",
    "blacklist-postgres.tar.gz",
    "blacklist-redis.tar.gz",
)
SERVER_NAME = "blacklist.example.test"
SERVICE_ID_VARIABLES = (
    "BLACKLIST_TLS_ROOT",
    "BLACKLIST_APP",
    "BLACKLIST_COLLECTOR",
    "BLACKLIST_POSTGRES",
    "BLACKLIST_REDIS",
    "BLACKLIST_FRONTEND",
)
FAKE_DOCKER = """#!/bin/sh
printf '%s\\n' "$*" >> "${TEST_DOCKER_LOG}"
case "${1:-}" in
    --version) echo "Docker version 29.2.1, build test" ;;
    compose) [ "${2:-}" = "version" ] && echo "2.40.0" ;;
    info|volume) exit 1 ;;
esac
exit 0
"""


class ReleaseKey(NamedTuple):
    home: Path
    fingerprint: str
    public_key: Path


def generate_release_key(tmp_path_factory: pytest.TempPathFactory, name: str) -> ReleaseKey:
    home = tmp_path_factory.mktemp(f"gnupg-{name}")
    home.chmod(0o700)
    environment = {**os.environ, "GNUPGHOME": str(home)}
    _ = subprocess.run(
        [
            "gpg",
            "--batch",
            "--pinentry-mode",
            "loopback",
            "--passphrase",
            "",
            "--quick-gen-key",
            f"Blacklist Test {name} <{name}@example.invalid>",
            "ed25519",
            "sign",
            "never",
        ],
        env=environment,
        capture_output=True,
        check=True,
    )
    listing = subprocess.run(
        ["gpg", "--batch", "--with-colons", "--list-keys"],
        env=environment,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    fingerprint = next(line.split(":")[9] for line in listing.splitlines() if line.startswith("fpr:"))
    public_key = tmp_path_factory.mktemp(f"operator-key-{name}") / "release-public-key.asc"
    _ = public_key.write_bytes(
        subprocess.run(
            ["gpg", "--batch", "--armor", "--export", fingerprint],
            env=environment,
            capture_output=True,
            check=True,
        ).stdout
    )
    return ReleaseKey(home, fingerprint, public_key)


def stop_gpg_agent(key: ReleaseKey) -> None:
    _ = subprocess.run(["gpgconf", "--homedir", str(key.home), "--kill", "all"], capture_output=True, check=False)


@pytest.fixture(scope="module")
def release_key(tmp_path_factory: pytest.TempPathFactory) -> Iterator[ReleaseKey]:
    key = generate_release_key(tmp_path_factory, "release")
    yield key
    stop_gpg_agent(key)


@pytest.fixture(scope="module")
def other_release_key(tmp_path_factory: pytest.TempPathFactory) -> Iterator[ReleaseKey]:
    key = generate_release_key(tmp_path_factory, "other")
    yield key
    stop_gpg_agent(key)


def prepare_bundle(root: Path, signing_key: ReleaseKey | None = None) -> Path:
    bundle = root / "bundle"
    images = bundle / "images"
    images.mkdir(parents=True)
    _ = shutil.copy2(INSTALLER, bundle / "install.sh")
    checksum_lines: list[str] = []
    for image_name in BUNDLE_IMAGES:
        payload = f"payload:{image_name}".encode()
        _ = (images / image_name).write_bytes(payload)
        checksum_lines.append(f"{hashlib.sha256(payload).hexdigest()}  {image_name}")
    _ = (images / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    _ = (bundle / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    _ = (bundle / "VERSION").write_text("0.0.0\n", encoding="utf-8")
    manifest_lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(bundle).as_posix()}"
        for path in sorted(bundle.rglob("*"))
        if path.is_file()
    ]
    _ = (bundle / "MANIFEST.sha256").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    if signing_key is not None:
        _ = subprocess.run(
            [
                "gpg",
                "--batch",
                "--yes",
                "--local-user",
                signing_key.fingerprint,
                "--armor",
                "--detach-sign",
                "--output",
                str(bundle / "MANIFEST.sha256.asc"),
                str(bundle / "MANIFEST.sha256"),
            ],
            env={**os.environ, "GNUPGHOME": str(signing_key.home)},
            capture_output=True,
            check=True,
        )
    return bundle


def installer_environment(root: Path) -> dict[str, str]:
    bin_dir = root / "bin"
    bin_dir.mkdir()
    real_id = shutil.which("id")
    assert real_id is not None
    fake_root_id = f'#!/bin/sh\nif [ "${{1:-}}" = "-u" ]; then echo 0; exit 0; fi\nexec {real_id} "$@"\n'
    for name, source in (("id", fake_root_id), ("docker", FAKE_DOCKER)):
        executable = bin_dir / name
        _ = executable.write_text(source, encoding="utf-8")
        executable.chmod(0o755)

    etc = root / "etc"
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{environment['PATH']}",
            "TEST_DOCKER_LOG": str(root / "docker.log"),
            "BLACKLIST_ENV_FILE": str(etc / ".env"),
            "BLACKLIST_TLS_DIR": str(etc / "tls"),
            "BLACKLIST_FRONTEND_TLS_DIR": str(etc / "frontend-tls"),
            "BLACKLIST_RELEASE_KEYRING": str(etc / "release-pubkey.gpg"),
            "FORTIGATE_TRUST_DIR": str(etc / "fortigate"),
        }
    )
    for prefix in SERVICE_ID_VARIABLES:
        environment[f"{prefix}_UID"] = str(os.getuid())
        environment[f"{prefix}_GID"] = str(os.getgid())
    return environment


def write_certificate(directory: Path, subject_alt_names: str) -> tuple[Path, Path]:
    directory.mkdir(exist_ok=True)
    certificate = directory / "server.crt"
    private_key = directory / "server.key"
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
            f"/CN={SERVER_NAME}",
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
    return certificate, private_key


def run_installer(bundle: Path, environment: dict[str, str], *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(bundle / "install.sh"), *arguments],
        cwd=bundle,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )


def one_command_arguments(key: ReleaseKey, certificate: Path, private_key: Path) -> tuple[str, ...]:
    return (
        "--release-key",
        str(key.public_key),
        "--fingerprint",
        key.fingerprint.lower(),
        "--server-name",
        SERVER_NAME,
        "--tls-cert",
        str(certificate),
        "--tls-key",
        str(private_key),
    )


def parse_env(env_file: Path) -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in env_file.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )


def test_missing_inputs_are_reported_together_before_any_change(tmp_path: Path) -> None:
    # Given: a bundle on a host without a release keyring, environment file, or certificate.
    bundle = prepare_bundle(tmp_path)
    environment = installer_environment(tmp_path)

    # When: the operator runs the installer without options.
    result = run_installer(bundle, environment)

    # Then: every missing input is listed in one run and the host is untouched.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert output.count("[FAIL]") == 3, output
    assert environment["BLACKLIST_RELEASE_KEYRING"] in output
    assert "--server-name" in output
    assert "--tls-cert" in output
    assert not (tmp_path / "etc").exists(), output
    assert not (tmp_path / "docker.log").exists(), output


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("--release-key", "key.asc"), "--release-key requires --fingerprint"),
        (("--fingerprint", "0" * 40), "--fingerprint requires --release-key"),
        (("--tls-cert", "server.crt"), "--tls-cert requires --tls-key"),
        (("--tls-key", "server.key"), "--tls-key requires --tls-cert"),
        (("--server-name",), "Option --server-name requires a value"),
        (("--check-secrets", "--server-name", SERVER_NAME), "apply only to installation"),
    ],
)
def test_incomplete_options_fail_before_privilege_checks(
    tmp_path: Path,
    arguments: tuple[str, ...],
    message: str,
) -> None:
    _ = shutil.copy2(INSTALLER, tmp_path / "install.sh")

    result = subprocess.run(
        ["bash", str(tmp_path / "install.sh"), *arguments],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert message in output, output
    assert "Root privileges" not in output, output


def test_key_with_a_different_fingerprint_is_never_registered(tmp_path: Path, release_key: ReleaseKey) -> None:
    bundle = prepare_bundle(tmp_path, release_key)
    environment = installer_environment(tmp_path)
    certificate, private_key = write_certificate(tmp_path / "operator", f"DNS:{SERVER_NAME}")
    arguments = list(one_command_arguments(release_key, certificate, private_key))
    arguments[3] = "0" * 40

    result = run_installer(bundle, environment, *arguments)

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "fingerprint mismatch" in output.lower(), output
    assert not Path(environment["BLACKLIST_RELEASE_KEYRING"]).exists()


def test_certificate_must_cover_the_server_name(tmp_path: Path, release_key: ReleaseKey) -> None:
    # Given: openssl -checkhost exits 0 on a mismatch, so only its verdict reveals this certificate.
    bundle = prepare_bundle(tmp_path, release_key)
    environment = installer_environment(tmp_path)
    certificate, private_key = write_certificate(tmp_path / "operator", "DNS:other.example.test")

    result = run_installer(bundle, environment, *one_command_arguments(release_key, certificate, private_key))

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert f"does not cover {SERVER_NAME}" in output, output
    assert not (tmp_path / "etc").exists(), output


def test_operator_files_inside_the_bundle_are_rejected_before_any_change(
    tmp_path: Path,
    release_key: ReleaseKey,
) -> None:
    bundle = prepare_bundle(tmp_path, release_key)
    environment = installer_environment(tmp_path)
    certificate, private_key = write_certificate(bundle / "tls", f"DNS:{SERVER_NAME}")

    result = run_installer(bundle, environment, *one_command_arguments(release_key, certificate, private_key))

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert output.count("outside the bundle directory") == 2, output
    assert not (tmp_path / "etc").exists(), output


def test_one_command_install_provisions_inputs_before_touching_docker(
    tmp_path: Path,
    release_key: ReleaseKey,
) -> None:
    # Given: a signed bundle and a fake Docker daemon that refuses the first volume mutation.
    bundle = prepare_bundle(tmp_path, release_key)
    environment = installer_environment(tmp_path)
    certificate, private_key = write_certificate(tmp_path / "operator", f"DNS:{SERVER_NAME}")

    # When: the operator runs the single documented command.
    result = run_installer(
        bundle,
        environment,
        "--skip-load",
        *one_command_arguments(release_key, certificate, private_key),
    )

    # Then: the run reaches the Docker mutation with every operator input provisioned.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "Unable to create collector volume blacklist_blacklist-collector-data" in output, output
    assert "Bundle manifest signature verified" in output, output

    keyring = subprocess.run(
        ["gpg", "--batch", "--with-colons", "--show-keys", environment["BLACKLIST_RELEASE_KEYRING"]],
        env={**os.environ, "GNUPGHOME": str(release_key.home)},
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    assert release_key.fingerprint in keyring

    env_file = Path(environment["BLACKLIST_ENV_FILE"])
    values = parse_env(env_file)
    assert values["FRONTEND_TLS_MODE"] == "provided"
    assert values["FRONTEND_TLS_SERVER_NAME"] == SERVER_NAME
    assert values["ADMIN_PASSWORD"] not in output

    password_file = Path(f"{env_file}.initial-admin-password")
    assert password_file.read_text(encoding="utf-8").strip() == values["ADMIN_PASSWORD"]
    assert stat.S_IMODE(password_file.stat().st_mode) == 0o600

    frontend_tls = Path(environment["BLACKLIST_FRONTEND_TLS_DIR"])
    assert (frontend_tls / "server.crt").read_bytes() == certificate.read_bytes()
    assert (frontend_tls / "server.key").read_bytes() == private_key.read_bytes()
    assert stat.S_IMODE((frontend_tls / "server.crt").stat().st_mode) == 0o644
    assert stat.S_IMODE((frontend_tls / "server.key").stat().st_mode) == 0o600

    docker_calls = (tmp_path / "docker.log").read_text(encoding="utf-8")
    assert (
        "volume create --label com.docker.compose.project=blacklist "
        "--label com.docker.compose.volume=blacklist-collector-data blacklist_blacklist-collector-data"
    ) in docker_calls


def test_existing_keyring_for_another_key_is_never_replaced(
    tmp_path: Path,
    release_key: ReleaseKey,
    other_release_key: ReleaseKey,
) -> None:
    # Given: the host already trusts a different release key.
    bundle = prepare_bundle(tmp_path, release_key)
    environment = installer_environment(tmp_path)
    keyring = Path(environment["BLACKLIST_RELEASE_KEYRING"])
    keyring.parent.mkdir(parents=True)
    _ = keyring.write_bytes(
        subprocess.run(
            ["gpg", "--batch", "--export", other_release_key.fingerprint],
            env={**os.environ, "GNUPGHOME": str(other_release_key.home)},
            capture_output=True,
            check=True,
        ).stdout
    )
    trusted = keyring.read_bytes()
    certificate, private_key = write_certificate(tmp_path / "operator", f"DNS:{SERVER_NAME}")

    # When: the operator passes another key with its matching fingerprint.
    result = run_installer(bundle, environment, *one_command_arguments(release_key, certificate, private_key))

    # Then: the existing trust anchor is kept and nothing else is created.
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert f"does not trust {release_key.fingerprint}" in output, output
    assert keyring.read_bytes() == trusted
    assert not Path(environment["BLACKLIST_ENV_FILE"]).exists(), output


def test_verify_only_checks_the_signature_with_the_given_key_without_registering_it(
    tmp_path: Path,
    release_key: ReleaseKey,
) -> None:
    bundle = prepare_bundle(tmp_path, release_key)
    environment = installer_environment(tmp_path)

    result = run_installer(
        bundle,
        environment,
        "--verify-only",
        "--require-signature",
        "--release-key",
        str(release_key.public_key),
        "--fingerprint",
        release_key.fingerprint,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Bundle manifest signature verified" in output, output
    assert not (tmp_path / "etc").exists(), output


def test_completion_output_uses_the_server_name_and_env_file(tmp_path: Path) -> None:
    installer = tmp_path / "install.sh"
    _ = installer.write_text(
        INSTALLER.read_text(encoding="utf-8").replace('\nmain "$@"\n', "\npost_install\n"),
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    _ = env_file.write_text(
        f"FRONTEND_TLS_MODE=provided\nFRONTEND_TLS_SERVER_NAME={SERVER_NAME}\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", str(installer)],
        capture_output=True,
        check=False,
        env={**os.environ, "BLACKLIST_ENV_FILE": str(env_file)},
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"https://{SERVER_NAME}" in result.stdout
    assert f"docker compose --env-file {env_file} -f {tmp_path / 'docker-compose.yml'} ps" in result.stdout
