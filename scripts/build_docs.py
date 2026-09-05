from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import cast


VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
IMAGE_PATTERN = re.compile(r"!\[[^]]*]\(([^)]+)\)")
VERSION_TOKEN = "저장소 루트 `VERSION` 기준"
MANIFEST_NAME = "pdf-sources.sha256"
PDF_MARKER_PREFIX = b"\n% blacklist-source-sha256:"
DOC_SPECS = (
    ("blacklist-admin-guide.md", "blacklist-admin-guide.pdf", "10pt", "15mm"),
    ("blacklist-user-guide.md", "blacklist-user-guide.pdf", "9pt", "12mm"),
    ("blacklist-offline-installation-guide.md", "blacklist-offline-deployment-guide.pdf", "10pt", "15mm"),
)
CommandRunner = Callable[[Sequence[str], Path, dict[str, str]], None]


def read_version(repo_root: Path) -> str:
    return parse_version((repo_root / "VERSION").read_bytes())


def parse_version(content: bytes) -> str:
    value = content.decode("utf-8").strip()
    if not VERSION_PATTERN.fullmatch(value):
        raise ValueError(f"invalid VERSION: {value}")
    return value


def source_snapshot(repo_root: Path) -> dict[Path, bytes]:
    manual = repo_root / "docs/manual"
    paths: set[Path] = {repo_root / "VERSION"}
    script = repo_root / "scripts/build_docs.py"
    if script.is_file():
        paths.add(script)
    for source_name, _output_name, _font_size, _margin in DOC_SPECS:
        source = manual / source_name
        paths.add(source)
        body = source.read_text(encoding="utf-8")
        for match in IMAGE_PATTERN.finditer(body):
            image = match.group(1).split("{")[0].strip()
            paths.add((manual / image).resolve())
    for path in paths:
        _ = path.relative_to(repo_root)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"documentation input must be a regular repository file: {path}")
    return {path: path.read_bytes() for path in sorted(paths)}


def snapshot_digest(repo_root: Path, snapshot: Mapping[Path, bytes]) -> str:
    digest = hashlib.sha256()
    for path, content in sorted(snapshot.items()):
        digest.update(path.relative_to(repo_root).as_posix().encode())
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def source_digest(repo_root: Path) -> str:
    return snapshot_digest(repo_root, source_snapshot(repo_root))


def run_command(command: Sequence[str], cwd: Path, environment: dict[str, str]) -> None:
    _ = subprocess.run(command, cwd=cwd, env=environment, check=True)


def pandoc_command(source: Path, output: Path, font_size: str, margin: str, version: str) -> list[str]:
    return [
        "pandoc",
        str(source),
        "--from=markdown-raw_tex-raw_attribute-yaml_metadata_block",
        "--sandbox",
        "--resource-path=.",
        "--pdf-engine=xelatex",
        "--metadata",
        f"version={version}",
        "-V",
        "papersize=a4",
        "-V",
        "lang=ko-KR",
        "-V",
        "mainfont=NanumGothic",
        "-V",
        "CJKmainfont=NanumGothic",
        "-V",
        "monofont=NanumGothicCoding",
        "-V",
        f"fontsize={font_size}",
        "-V",
        f"geometry:margin={margin}",
        "-V",
        "colorlinks=true",
        "-V",
        "linkcolor=blue",
        "-V",
        "filecolor=blue",
        "-V",
        "urlcolor=blue",
        "--toc",
        "--output",
        str(output),
    ]


def build(repo_root: Path, runner: CommandRunner = run_command) -> None:
    snapshot = source_snapshot(repo_root)
    version = parse_version(snapshot[repo_root / "VERSION"])
    digest = snapshot_digest(repo_root, snapshot)
    manual = repo_root / "docs/manual"
    environment = dict(os.environ, SOURCE_DATE_EPOCH="0")
    with tempfile.TemporaryDirectory(dir=manual) as temporary_directory:
        temporary = Path(temporary_directory)
        generated: list[tuple[Path, Path]] = []
        for path, content in snapshot.items():
            try:
                relative_path = path.relative_to(manual)
            except ValueError:
                continue
            snapshot_path = temporary / relative_path
            _ = snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            _ = snapshot_path.write_bytes(content)
        for source_name, output_name, font_size, margin in DOC_SPECS:
            body = snapshot[manual / source_name].decode("utf-8").replace(VERSION_TOKEN, version)
            source = temporary / source_name
            _ = source.write_text(body, encoding="utf-8")
            output = temporary / output_name
            runner(pandoc_command(source, output, font_size, margin, version), temporary, environment)
            if not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError(f"pandoc did not create {output_name}")
            with output.open("ab") as pdf:
                _ = pdf.write(PDF_MARKER_PREFIX + digest.encode() + b"\n")
            generated.append((output, manual / output_name))
        if source_digest(repo_root) != digest:
            raise RuntimeError("documentation sources changed during PDF generation")
        for source, destination in generated:
            os.replace(source, destination)
        manifest = temporary / MANIFEST_NAME
        _ = manifest.write_text(f"{digest}\n", encoding="utf-8")
        os.replace(manifest, manual / MANIFEST_NAME)


def check(repo_root: Path) -> bool:
    manual = repo_root / "docs/manual"
    manifest = manual / MANIFEST_NAME
    digest = source_digest(repo_root)
    if not manifest.is_file() or manifest.read_text(encoding="utf-8").strip() != digest:
        return False
    marker = PDF_MARKER_PREFIX + digest.encode() + b"\n"
    return all(
        (manual / output_name).is_file() and (manual / output_name).read_bytes().endswith(marker)
        for _, output_name, _, _ in DOC_SPECS
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    if cast(bool, arguments.check):
        if check(repo_root):
            return 0
        print("PDF sources or outputs are stale")
        return 1
    build(repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
