from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .integrity import BundleError


SERVICES: Final = ("app", "collector", "frontend", "postgres", "redis")


@dataclass(frozen=True, slots=True)
class BuildSpec:
    """How one service image is built, mirroring the release pipeline matrix."""

    service: str
    context: str
    dockerfile: str


BUILD_SPECS: Final = (
    BuildSpec("app", ".", "app/Dockerfile"),
    BuildSpec("collector", ".", "collector/Dockerfile"),
    BuildSpec("frontend", ".", "frontend/Dockerfile"),
    BuildSpec("postgres", "postgres", "postgres/Dockerfile"),
    BuildSpec("redis", ".", "deploy/redis/Dockerfile"),
)


def build_command(spec: BuildSpec, version: str, commit: str) -> list[str]:
    """Return the docker build invocation for one service."""
    return [
        "docker",
        "build",
        "-f",
        spec.dockerfile,
        "-t",
        f"blacklist-{spec.service}:{version}",
        "--build-arg",
        f"APP_VERSION={version}",
        "--build-arg",
        f"GIT_COMMIT={commit}",
        spec.context,
    ]


def current_commit(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )
    return result.stdout.strip() or "unknown"


def run(command: list[str], *, cwd: Path | None = None) -> None:
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode != 0:
        raise BundleError(f"Command failed ({result.returncode}): {' '.join(command)}")


def build_images(repo_root: Path, version: str) -> None:
    """Build every service image at the resolved release tag."""
    commit = current_commit(repo_root)
    for spec in BUILD_SPECS:
        print(f"building blacklist-{spec.service}:{version}", file=sys.stderr)
        run(build_command(spec, version, commit), cwd=repo_root)


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
                + "would ship a tag the compose files cannot resolve."
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
