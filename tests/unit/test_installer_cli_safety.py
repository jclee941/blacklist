from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


INSTALLER = Path(__file__).parents[2] / "deploy" / "install.sh"


def run_installer(tmp_path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    installer = tmp_path / "install.sh"
    _ = shutil.copy2(INSTALLER, installer)

    return subprocess.run(
        ["bash", str(installer), *arguments],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )


def test_installer_syntax_is_valid() -> None:
    # Given: the offline installer as shipped inside the release bundle.

    # When: the shell parses the script without executing it.
    result = subprocess.run(["bash", "-n", str(INSTALLER)], capture_output=True, check=False, text=True)

    # Then: the script is syntactically valid.
    assert result.returncode == 0, result.stdout + result.stderr


def test_help_lists_new_flags(tmp_path: Path) -> None:
    # Given: an operator without root privileges reading the installer usage.

    # When: help is requested.
    result = run_installer(tmp_path, "--help")

    # Then: the read-only verification mode is documented.
    assert result.returncode == 0, result.stdout + result.stderr
    assert "--verify-only" in result.stdout
