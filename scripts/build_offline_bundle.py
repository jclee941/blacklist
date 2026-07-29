#!/usr/bin/env python3
"""Build the Blacklist offline deployment bundle locally.

The release version is always derived from the repository's VERSION file, so a
bundle can never be tagged by hand and drift from what the installer expects.

This builder exists because the shipped bundle carries a MANIFEST.sha256 that
`deploy/install.sh` now treats as mandatory, while the GitHub release workflow
never produced one. Packaging runs here instead of in CI.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path


SERVICES = ("app", "collector", "frontend", "postgres", "redis")
MANIFEST_NAME = "MANIFEST.sha256"
CHECKSUMS_NAME = "checksums.sha256"


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
    lines = [
        f"{sha256_of(image)}  {image.name}"
        for image in sorted(images_dir.glob("*.tar.gz"))
    ]
    if not lines:
        raise BundleError(f"No image archives found in {images_dir}")
    _ = (images_dir / CHECKSUMS_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(bundle_dir: Path) -> None:
    """Hash every bundled file except the manifest itself.

    Paths are recorded bare and relative to the bundle root because
    `verify_manifest()` runs `sha256sum -c` from there. A checksum file cannot
    contain its own hash, so the manifest is the single exclusion.
    """
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
    stamped = [
        f"VERSION={version}" if line.startswith("VERSION=") else line for line in lines
    ]
    if stamped == lines:
        raise BundleError(f"{installer} declares no VERSION= line to stamp")
    _ = installer.write_text("\n".join(stamped) + "\n", encoding="utf-8")


def run(command: list[str], *, cwd: Path | None = None) -> None:
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode != 0:
        raise BundleError(f"Command failed ({result.returncode}): {' '.join(command)}")


def export_images(images_dir: Path, version: str) -> None:
    """Save each service image at the release tag into the bundle."""
    images_dir.mkdir(parents=True, exist_ok=True)
    for service in SERVICES:
        reference = f"blacklist-{service}:{version}"
        inspect = subprocess.run(
            ["docker", "image", "inspect", reference],
            capture_output=True,
            check=False,
        )
        if inspect.returncode != 0:
            raise BundleError(
                f"Image {reference} is not present. Build it first, or the bundle "
                "would ship a tag the compose files cannot resolve."
            )
        archive = images_dir / f"blacklist-{service}.tar.gz"
        with archive.open("wb") as handle:
            save = subprocess.Popen(["docker", "save", reference], stdout=subprocess.PIPE)
            assert save.stdout
            gzip_proc = subprocess.Popen(["gzip", "-n"], stdin=save.stdout, stdout=handle)
            save.stdout.close()
            _ = gzip_proc.communicate()
            _ = save.wait()
            if save.returncode != 0 or gzip_proc.returncode != 0:
                raise BundleError(f"Failed to export {reference}")

def missing_prereqs(prereqs_dir: Path) -> list[str]:
    """Report offline prerequisites the installer needs but the bundle lacks.

    `install_docker_offline()` extracts `prereqs/docker-*.tgz` and copies the
    compose binary as root on a host with no Docker. Without them the bundle
    silently cannot bootstrap a bare target.
    """
    missing: list[str] = []
    if not any(prereqs_dir.glob("docker-*.tgz")):
        missing.append("docker-*.tgz")
    if not (prereqs_dir / "docker-compose-linux-x86_64").is_file():
        missing.append("docker-compose-linux-x86_64")
    if not (prereqs_dir / "docker.service").is_file():
        missing.append("docker.service")
    return missing


def assemble(repo_root: Path, bundle_dir: Path, version: str) -> None:
    """Copy the deployment surface into the bundle."""
    deploy = repo_root / "deploy"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    _ = shutil.copy2(deploy / "docker-compose.release.yml", bundle_dir / "docker-compose.yml")
    _ = shutil.copy2(deploy / "base.yml", bundle_dir / "base.yml")
    _ = shutil.copy2(deploy / "install.sh", bundle_dir / "install.sh")
    (bundle_dir / "install.sh").chmod(0o755)

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


def build(repo_root: Path, output_dir: Path, *, skip_images: bool) -> Path:
    version = resolve_version(repo_root)
    bundle_dir = output_dir / f"blacklist-{version}"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    assemble(repo_root, bundle_dir, version)
    # Stamp before hashing: a manifest built over the pre-stamp installer would
    # record a hash the installer can never match, aborting every install.
    stamp_installer_version(bundle_dir / "install.sh", version)

    if not skip_images:
        export_images(bundle_dir / "images", version)
    write_image_checksums(bundle_dir / "images")
    write_manifest(bundle_dir)

    for item in missing_prereqs(bundle_dir / "prereqs"):
        print(
            f"warning: prereqs/{item} is absent; this bundle cannot install Docker "
            "on a host that does not already have it",
            file=sys.stderr,
        )

    return pack(bundle_dir, output_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--output", type=Path, default=Path("release"), help="where to write the bundle"
    )
    _ = parser.add_argument(
        "--skip-images",
        action="store_true",
        help="reuse image archives already present in the bundle directory",
    )
    arguments = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    try:
        archive = build(repo_root, (repo_root / arguments.output).resolve(), skip_images=arguments.skip_images)
    except BundleError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
