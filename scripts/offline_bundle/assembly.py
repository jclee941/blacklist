from __future__ import annotations

import re
import shutil
from pathlib import Path

from .integrity import BundleError


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
    """Copy the deployment surface into the bundle."""
    deploy = repo_root / "deploy"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    _ = shutil.copy2(deploy / "docker-compose.release.yml", bundle_dir / "docker-compose.yml")
    _ = shutil.copy2(deploy / "base.yml", bundle_dir / "base.yml")
    _ = shutil.copy2(deploy / "install.sh", bundle_dir / "install.sh")
    (bundle_dir / "install.sh").chmod(0o755)

    # Derive bind-mount sources so Docker cannot silently create missing paths.
    base_yml = (deploy / "base.yml").read_text(encoding="utf-8")
    for source in sorted(set(re.findall(r"-\s+\./([\w./-]+):", base_yml))):
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

    guide = repo_root / "docs" / "manual" / "blacklist-offline-deployment-guide.pdf"
    if guide.is_file():
        (bundle_dir / "docs").mkdir(exist_ok=True)
        _ = shutil.copy2(guide, bundle_dir / "docs" / guide.name)

    _ = (bundle_dir / "VERSION").write_text(f"{version}\n", encoding="utf-8")
