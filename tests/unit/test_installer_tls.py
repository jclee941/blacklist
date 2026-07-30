from __future__ import annotations

import gzip
import hashlib
import os
import shutil
import stat
import subprocess
from pathlib import Path


DEPLOY_DIR = Path(__file__).parents[2] / "deploy"
INSTALLER = DEPLOY_DIR / "install.sh"
BUNDLE_IMAGES = (
    "blacklist-app.tar.gz",
    "blacklist-collector.tar.gz",
    "blacklist-frontend.tar.gz",
    "blacklist-postgres.tar.gz",
    "blacklist-redis.tar.gz",
)
FAKE_SS = """#!/bin/sh
exit 0
"""
STUB_SECRETS = {
    "COMPOSE_PROJECT_NAME": "blacklist",
    "CREDENTIAL_MASTER_KEY": "local-credential-master-key-0123456789",
    "SECRET_KEY": "local-secret-key-0123456789",
    "CREDENTIAL_ENCRYPTION_KEY": "local-credential-encryption-key-0123456789",
    "ENCRYPTION_SALT": "local-encryption-salt-0123456789",
    "POSTGRES_PASSWORD": "local-postgres-password-0123456789",
    "REDIS_PASSWORD": "local-redis-password-0123456789",
    "COLLECTOR_AUTH_TOKEN": "local-collector-auth-token-0123456789",
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD": "local-admin-password-0123456789",
    "BLACKLIST_VERSION": "0.0.0-test",
}
SERVICE_NAMES = (
    "blacklist-app",
    "blacklist-collector",
    "blacklist-postgres",
    "blacklist-redis",
)


def write_manifest(bundle_dir: Path) -> None:
    """Regenerate MANIFEST.sha256 from the bundle's CURRENT contents.

    Manifest verification runs before the posture gate, so a scratch bundle whose
    manifest does not match would be rejected for integrity reasons and the
    posture invariant under test would never be reached.
    """
    manifest = bundle_dir / "MANIFEST.sha256"
    manifest.unlink(missing_ok=True)
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(bundle_dir).as_posix()}"
        for path in sorted(bundle_dir.rglob("*"))
        if path.is_file()
    ]
    _ = manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def installer_environment(tls_dir: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "BLACKLIST_TLS_DIR": str(tls_dir),
            "BLACKLIST_TLS_ROOT_UID": str(os.getuid()),
            "BLACKLIST_TLS_ROOT_GID": str(os.getgid()),
            "BLACKLIST_APP_UID": str(os.getuid()),
            "BLACKLIST_APP_GID": str(os.getgid()),
            "BLACKLIST_COLLECTOR_UID": str(os.getuid()),
            "BLACKLIST_COLLECTOR_GID": str(os.getgid()),
            "BLACKLIST_POSTGRES_UID": str(os.getuid()),
            "BLACKLIST_POSTGRES_GID": str(os.getgid()),
            "BLACKLIST_REDIS_UID": str(os.getuid()),
            "BLACKLIST_REDIS_GID": str(os.getgid()),
        }
    )
    return environment


def run_tls_setup(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    installer = tmp_path / "install.sh"
    installer_source = INSTALLER.read_text(encoding="utf-8")
    _ = installer.write_text(
        installer_source.replace('\nmain "$@"\n', "\nsetup_internal_tls\n"),
        encoding="utf-8",
    )
    tls_dir = tmp_path / "etc" / "blacklist" / "tls"
    return subprocess.run(
        ["bash", str(installer)],
        capture_output=True,
        check=False,
        env=installer_environment(tls_dir),
        text=True,
    )


def prepare_verify_bundle(tmp_path: Path) -> tuple[dict[str, str], Path]:
    _ = shutil.copy2(INSTALLER, tmp_path / "install.sh")
    _ = shutil.copy2(DEPLOY_DIR / "base.yml", tmp_path / "base.yml")
    _ = shutil.copy2(DEPLOY_DIR / "docker-compose.yml", tmp_path / "docker-compose.yml")

    images_dir = tmp_path / "images"
    images_dir.mkdir()
    checksum_lines: list[str] = []
    for image_name in BUNDLE_IMAGES:
        payload = gzip.compress(b"fake-image-archive")
        _ = (images_dir / image_name).write_bytes(payload)
        checksum_lines.append(f"{hashlib.sha256(payload).hexdigest()}  {image_name}")
    _ = (images_dir / "checksums.sha256").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )

    env_file = tmp_path / "etc" / ".env"
    env_file.parent.mkdir()
    _ = env_file.write_text(
        "\n".join(f"{key}={value}" for key, value in STUB_SECRETS.items()) + "\n",
        encoding="utf-8",
    )
    tls_dir = tmp_path / "etc" / "blacklist" / "tls"
    environment = installer_environment(tls_dir)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    ss = bin_dir / "ss"
    _ = ss.write_text(FAKE_SS, encoding="utf-8")
    _ = ss.chmod(0o755)
    environment["PATH"] = f"{bin_dir}{os.pathsep}{environment['PATH']}"
    environment["BLACKLIST_ENV_FILE"] = str(env_file)
    write_manifest(tmp_path)
    return environment, tls_dir


def test_installer_generates_local_ca_and_service_sans(tmp_path: Path) -> None:
    result = run_tls_setup(tmp_path)

    output = result.stdout + result.stderr
    assert result.returncode == 0, output

    tls_dir = tmp_path / "etc" / "blacklist" / "tls"
    ca_cert = tls_dir / "ca" / "ca.crt"
    assert ca_cert.is_file()
    for service_name in SERVICE_NAMES:
        service_dir = tls_dir / service_name.removeprefix("blacklist-")
        cert = service_dir / "tls.crt"
        assert (service_dir / "tls.key").is_file()
        certificate = subprocess.run(
            ["openssl", "x509", "-in", str(cert), "-noout", "-ext", "subjectAltName"],
            capture_output=True,
            check=True,
            text=True,
        )
        assert f"DNS:{service_name}" in certificate.stdout


def test_generate_tls_only_runs_the_reusable_tls_setup(tmp_path: Path) -> None:
    tls_dir = tmp_path / "tls"

    result = subprocess.run(
        ["bash", str(INSTALLER), "--generate-tls-only"],
        capture_output=True,
        check=False,
        env=installer_environment(tls_dir),
        text=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Generated target-local CA and service certificates" in output
    assert (tls_dir / "ca" / "ca.crt").is_file()


def test_installer_protects_private_keys_and_directories(tmp_path: Path) -> None:
    result = run_tls_setup(tmp_path)

    output = result.stdout + result.stderr
    assert result.returncode == 0, output

    tls_dir = tmp_path / "etc" / "blacklist" / "tls"
    assert stat.S_IMODE(tls_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE((tls_dir / "ca").stat().st_mode) == 0o700
    assert stat.S_IMODE((tls_dir / "ca" / "ca.key").stat().st_mode) == 0o600
    assert stat.S_IMODE((tls_dir / "ca" / "ca.crt").stat().st_mode) == 0o644
    for service_name in SERVICE_NAMES:
        service_dir = tls_dir / service_name.removeprefix("blacklist-")
        assert stat.S_IMODE(service_dir.stat().st_mode) == 0o700
        assert stat.S_IMODE((service_dir / "tls.key").stat().st_mode) == 0o600
        assert stat.S_IMODE((service_dir / "tls.crt").stat().st_mode) == 0o644
        assert (service_dir / "tls.key").stat().st_uid == os.getuid()
        assert (service_dir / "tls.key").stat().st_gid == os.getgid()


def test_verify_only_does_not_generate_certificates(tmp_path: Path) -> None:
    environment, tls_dir = prepare_verify_bundle(tmp_path)

    result = subprocess.run(
        ["bash", str(tmp_path / "install.sh"), "--verify-only", "--skip-posture-check"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert not tls_dir.exists()


def test_deploy_bundle_tracks_no_certificates_or_private_keys() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "deploy"],
        cwd=DEPLOY_DIR.parent,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.splitlines()

    assert all(Path(path).suffix not in {".crt", ".key", ".pem"} for path in tracked)
