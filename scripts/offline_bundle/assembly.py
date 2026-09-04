from __future__ import annotations

import io
import re
import shutil
import subprocess
import tarfile
from pathlib import Path
from typing import Final

from .integrity import BundleError


OPERATOR_DOCUMENTS: Final[tuple[tuple[str, str], ...]] = (
    ("blacklist-offline-package-guide.md", "README.md"),
    ("blacklist-user-guide.md", "blacklist-user-guide.md"),
    ("blacklist-user-guide.pdf", "blacklist-user-guide.pdf"),
    ("blacklist-admin-guide.md", "blacklist-admin-guide.md"),
    ("blacklist-admin-guide.pdf", "blacklist-admin-guide.pdf"),
    ("blacklist-offline-deployment-guide.pdf", "blacklist-offline-deployment-guide.pdf"),
    ("blacklist-offline-installation-guide.md", "blacklist-offline-installation-guide.md"),
    ("blacklist-operations-guide.md", "blacklist-operations-guide.md"),
    ("security-remediation-2026-07-28.md", "security-remediation-2026-07-28.md"),
    ("security-remediation-checklist.md", "security-remediation-checklist.md"),
    ("security-remediation-validation-report.md", "security-remediation-validation-report.md"),
    ("screenshots/login.png", "screenshots/login.png"),
    ("screenshots/dashboard.png", "screenshots/dashboard.png"),
    ("screenshots/ip-management.png", "screenshots/ip-management.png"),
    ("screenshots/collection.png", "screenshots/collection.png"),
    ("screenshots/analytics.png", "screenshots/analytics.png"),
    ("screenshots/fortinet.png", "screenshots/fortinet.png"),
    ("screenshots/cloudflare.png", "screenshots/cloudflare.png"),
    ("screenshots/database.png", "screenshots/database.png"),
)
SOURCE_ROOTS: Final[tuple[str, ...]] = ("app", "collector", "frontend", "postgres")
SOURCE_EXCLUSIONS: Final[tuple[str, ...]] = (
    ":(exclude)frontend/.env.e2e",
    ":(glob,exclude)**/AGENTS.md",
)


def prereq_gaps(prereqs_dir: Path) -> list[str]:
    """Report a half-shipped offline Docker payload."""
    payload = {
        "docker-*.tgz": any(prereqs_dir.glob("docker-*.tgz")),
        "docker-compose-linux-x86_64": (prereqs_dir / "docker-compose-linux-x86_64").is_file(),
    }
    if not any(payload.values()):
        return []
    return [name for name, present in payload.items() if not present]


def assemble(repo_root: Path, bundle_dir: Path, version: str) -> None:
    deploy = repo_root / "deploy"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    source_archive = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD", "--", *SOURCE_ROOTS, *SOURCE_EXCLUSIONS],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if source_archive.returncode != 0:
        detail = source_archive.stderr.decode(errors="replace").strip()
        raise BundleError(f"Cannot archive release source: {detail}")
    source_dir = bundle_dir / "source"
    source_dir.mkdir()
    try:
        with tarfile.open(fileobj=io.BytesIO(source_archive.stdout), mode="r:") as archive:
            archive.extractall(source_dir, filter="data")
    except (OSError, tarfile.TarError) as error:
        raise BundleError(f"Cannot extract release source: {error}") from error

    _ = shutil.copy2(deploy / "docker-compose.release.yml", bundle_dir / "docker-compose.yml")
    _ = shutil.copy2(deploy / "base.yml", bundle_dir / "base.yml")
    _ = shutil.copy2(deploy / "install.sh", bundle_dir / "install.sh")
    (bundle_dir / "install.sh").chmod(0o755)

    # Derive bind-mount sources so Docker cannot silently create missing paths.
    base_yml = (deploy / "base.yml").read_text(encoding="utf-8")
    bind_mount_sources: set[str] = set(re.findall(r"-\s+\./([\w./-]+):", base_yml))
    for source in sorted(bind_mount_sources):
        origin = deploy / source
        if not origin.is_file():
            raise BundleError(f"base.yml bind-mounts ./{source} but deploy/{source} does not exist")
        destination = bundle_dir / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.copy2(origin, destination)

    prereqs = deploy / "prereqs"
    if prereqs.is_dir():
        _ = shutil.copytree(prereqs, bundle_dir / "prereqs", dirs_exist_ok=True)

    notes = repo_root / "docs" / "manual" / f"blacklist-{version}-release-notes.md"
    if notes.is_file():
        _ = shutil.copy2(notes, bundle_dir / "RELEASE_NOTES.md")

    manual_dir = repo_root / "docs" / "manual"
    bundle_docs = bundle_dir / "docs"
    bundle_docs.mkdir(exist_ok=True)
    for source_name, destination_name in OPERATOR_DOCUMENTS:
        source = manual_dir / source_name
        if not source.is_file():
            raise BundleError(f"required operator document is missing: docs/manual/{source_name}")
        destination = bundle_docs / destination_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.copy2(source, destination)

    _ = (bundle_dir / "VERSION").write_text(f"{version}\n", encoding="utf-8")
