from __future__ import annotations

import hashlib
import tarfile
from pathlib import Path
from typing import Final


MANIFEST_NAME: Final = "MANIFEST.sha256"
CHECKSUMS_NAME: Final = "checksums.sha256"


class BundleError(RuntimeError):
    """A packaging precondition was not met."""


def resolve_version(repo_root: Path) -> str:
    """Return the release version recorded in the repository."""
    version_file = repo_root / "VERSION"
    try:
        version = version_file.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise BundleError(f"Cannot read {version_file}: {error}") from error
    if not version:
        raise BundleError(f"{version_file} is empty")
    return version


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_image_checksums(images_dir: Path) -> None:
    """Record image hashes using the bare-filename form the installer expects."""
    lines = [f"{sha256_of(image)}  {image.name}" for image in sorted(images_dir.glob("*.tar.gz"))]
    if not lines:
        raise BundleError(f"No image archives found in {images_dir}")
    _ = (images_dir / CHECKSUMS_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(bundle_dir: Path) -> None:
    """Hash every bundled file except the manifest and its signature."""
    lines = [
        f"{sha256_of(path)}  {path.relative_to(bundle_dir).as_posix()}"
        for path in sorted(bundle_dir.rglob("*"))
        if path.is_file() and path.name not in {MANIFEST_NAME, f"{MANIFEST_NAME}.asc"}
    ]
    if not lines:
        raise BundleError(f"Refusing to write an empty manifest for {bundle_dir}")
    _ = (bundle_dir / MANIFEST_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def stamp_installer_version(installer: Path, version: str) -> None:
    """Pin the bundled installer to this release before it is hashed."""
    lines = installer.read_text(encoding="utf-8").splitlines()
    stamped = [f"VERSION={version}" if line.startswith("VERSION=") else line for line in lines]
    if stamped == lines:
        raise BundleError(f"{installer} declares no VERSION= line to stamp")
    _ = installer.write_text("\n".join(stamped) + "\n", encoding="utf-8")


def pack(bundle_dir: Path, output_dir: Path) -> Path:
    """Create the reproducible tarball and its detached checksum."""
    archive = output_dir / f"{bundle_dir.name}.tar.gz"

    def normalise(entry: tarfile.TarInfo) -> tarfile.TarInfo:
        entry.uid = 0
        entry.gid = 0
        entry.uname = ""
        entry.gname = ""
        return entry

    with tarfile.open(archive, "w:gz") as tar:
        tar.add(bundle_dir, arcname=bundle_dir.name, filter=normalise)

    _ = (output_dir / f"{archive.name}.sha256").write_text(
        f"{sha256_of(archive)}  {archive.name}\n", encoding="utf-8"
    )
    return archive
