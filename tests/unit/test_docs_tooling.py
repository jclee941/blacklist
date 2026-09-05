import os
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[2]
ACTIVE_VERSION_DOCS = (
    ROOT / "frontend/README.md",
    ROOT / "collector/README.md",
    ROOT / "docs/README.md",
    ROOT / "docs/manual/blacklist-admin-guide.md",
    ROOT / "docs/manual/blacklist-user-guide.md",
    ROOT / "docs/testing/TEST-GUIDE-MAIN.md",
)


def test_docs_tooling_covers_ignored_tracked_files() -> None:
    config = (ROOT / ".markdownlint-cli2.jsonc").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    pdf_builder = (ROOT / "scripts/build_docs.py").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert '"gitignore": false' in config
    assert "git ls-files -z -- '*.md'" in makefile
    assert "xargs -0" in makefile
    assert "--ignore-path /dev/null" in makefile
    assert "docs-pdf:" in makefile
    assert "python3 scripts/build_docs.py" in makefile
    assert "--from=markdown" in pdf_builder
    assert "VERSION_PATTERN" in pdf_builder
    assert "os.replace" in pdf_builder
    assert "!docs/manual/pdf-sources.sha256" in gitignore


def test_docs_check_treats_special_filename_as_one_argument(tmp_path: Path) -> None:
    _ = shutil.copy(ROOT / "Makefile", tmp_path / "Makefile")
    malicious_name = "review.md;touch DOCS_TOOLING_INJECTION;#.md"
    _ = (tmp_path / malicious_name).write_text("# Safe\n", encoding="utf-8")
    _ = (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    scripts = tmp_path / "scripts"
    _ = scripts.mkdir()
    _ = (scripts / "build_docs.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _ = bin_dir.mkdir()
    npx_log = tmp_path / "npx.log"
    npx = bin_dir / "npx"
    _ = npx.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$NPX_LOG"\n', encoding="utf-8")
    _ = npx.chmod(0o755)
    environment = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}", NPX_LOG=str(npx_log))
    _ = subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    _ = subprocess.run(["git", "add", malicious_name], cwd=tmp_path, check=True)

    result = subprocess.run(
        ["make", "docs-check"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "DOCS_TOOLING_INJECTION").exists()
    assert malicious_name in npx_log.read_text(encoding="utf-8")


def test_active_unversioned_guides_reference_the_root_version() -> None:
    for document in ACTIVE_VERSION_DOCS:
        content = document.read_text(encoding="utf-8")
        assert "VERSION" in content
        assert re.search(r"(?:Version|version|버전).{0,20}`?\d+\.\d+\.\d+", content) is None
