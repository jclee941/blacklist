#!/usr/bin/env python3
"""Build the Blacklist offline deployment bundle locally."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

# File-path imports and direct execution need the repository package root on sys.path.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.offline_bundle import (
    BUILD_SPECS,
    SERVICES,
    BuildSpec,
    BundleError,
    assemble,
    build_command,
    build_images,
    current_commit,
    export_images,
    pack,
    prereq_gaps,
    resolve_version,
    sha256_of,
    stamp_installer_version,
    write_image_checksums,
    write_manifest,
)

__all__ = [
    "BUILD_SPECS",
    "SERVICES",
    "BuildSpec",
    "BundleError",
    "assemble",
    "build",
    "build_command",
    "build_images",
    "current_commit",
    "export_images",
    "main",
    "pack",
    "prereq_gaps",
    "resolve_version",
    "sha256_of",
    "stamp_installer_version",
    "write_image_checksums",
    "write_manifest",
]


def build(repo_root: Path, output_dir: Path, *, skip_images: bool, rebuild: bool) -> Path:
    version = resolve_version(repo_root)
    bundle_dir = output_dir / f"blacklist-{version}"
    output_dir.mkdir(parents=True, exist_ok=True)
    if bundle_dir.exists():
        if skip_images:
            with tempfile.TemporaryDirectory(dir=output_dir) as staging_dir:
                staged_images = Path(staging_dir) / "images"
                images_dir = bundle_dir / "images"
                if images_dir.is_dir():
                    _ = shutil.copytree(images_dir, staged_images)
                shutil.rmtree(bundle_dir)
                if staged_images.is_dir():
                    _ = shutil.copytree(staged_images, bundle_dir / "images")
        else:
            shutil.rmtree(bundle_dir)

    if rebuild:
        build_images(repo_root, version)

    assemble(repo_root, bundle_dir, version)
    stamp_installer_version(bundle_dir / "install.sh", version)
    if not skip_images:
        export_images(bundle_dir / "images", version)
    write_image_checksums(bundle_dir / "images")
    write_manifest(bundle_dir)

    for item in prereq_gaps(bundle_dir / "prereqs"):
        print(
            f"warning: prereqs/{item} is missing while the rest of the offline Docker "
            + "payload is present; a partial payload fails mid-install as root",
            file=sys.stderr,
        )

    return pack(bundle_dir, output_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--output", type=Path, default=Path("release"), help="where to write the bundle")
    _ = parser.add_argument(
        "--skip-images",
        action="store_true",
        help="reuse image archives already present in the bundle directory",
    )
    _ = parser.add_argument(
        "--build",
        action="store_true",
        help="build every service image at the resolved version before packaging",
    )
    arguments = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    try:
        archive = build(
            repo_root,
            (repo_root / arguments.output).resolve(),
            skip_images=arguments.skip_images,
            rebuild=arguments.build,
        )
    except BundleError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
