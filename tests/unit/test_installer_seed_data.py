from __future__ import annotations

import gzip
import os
import subprocess
from pathlib import Path


INSTALLER = Path(__file__).parents[2] / "deploy" / "install.sh"
SEED_CSV = "ip_address,reason,source\n198.51.100.7,REGTECH advisory,REGTECH\n"
DOCKER_STUB = """#!/bin/sh
printf '%s\\n' "$*" >> "$DOCKER_LOG"
case "$*" in
    *"SELECT COUNT(*)"*) printf '%s\\n' "$DOCKER_ROW_COUNT" ;;
    *"COPY blacklist_ips ("*) cat > "$DOCKER_COPY_CAPTURE" ;;
    *"COPY (SELECT"*) printf '%s' "$DOCKER_EXPORT_CSV" ;;
    inspect*) exit 0 ;;
esac
"""


def installer_environment(tmp_path: Path, row_count: str) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    _ = docker.write_text(DOCKER_STUB, encoding="utf-8")
    docker.chmod(0o755)
    environment = os.environ.copy()
    environment.update(
        PATH=f"{bin_dir}{os.pathsep}{environment['PATH']}",
        DOCKER_LOG=str(tmp_path / "docker.log"),
        DOCKER_ROW_COUNT=row_count,
        DOCKER_COPY_CAPTURE=str(tmp_path / "copied.csv"),
        DOCKER_EXPORT_CSV=SEED_CSV,
    )
    return environment


def run_seed_import(tmp_path: Path, row_count: str, *, with_seed: bool = True) -> subprocess.CompletedProcess[str]:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    installer = bundle / "install.sh"
    _ = installer.write_text(
        INSTALLER.read_text(encoding="utf-8").replace('\nmain "$@"\n', "\nimport_seed_data\n"), encoding="utf-8"
    )
    if with_seed:
        (bundle / "seed").mkdir()
        _ = (bundle / "seed" / "blacklist_ips.csv.gz").write_bytes(gzip.compress(SEED_CSV.encode()))
    return subprocess.run(
        ["bash", str(installer)],
        capture_output=True,
        check=False,
        env=installer_environment(tmp_path, row_count),
        text=True,
    )


def test_seed_data_is_imported_into_an_empty_database(tmp_path: Path) -> None:
    result = run_seed_import(tmp_path, "0")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "copied.csv").read_text(encoding="utf-8") == SEED_CSV
    assert "COPY blacklist_ips (ip_address," in (tmp_path / "docker.log").read_text(encoding="utf-8")


def test_seed_data_never_touches_a_database_that_has_rows(tmp_path: Path) -> None:
    result = run_seed_import(tmp_path, "12")

    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "copied.csv").exists()
    assert "already holds 12 rows" in result.stdout


def test_bundle_without_seed_data_skips_the_import(tmp_path: Path) -> None:
    result = run_seed_import(tmp_path, "0", with_seed=False)

    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "docker.log").exists()


def test_export_writes_blacklist_ips_as_gzip_csv(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    installer = bundle / "install.sh"
    _ = installer.write_text(INSTALLER.read_text(encoding="utf-8"), encoding="utf-8")
    destination = tmp_path / "blacklist-seed.csv.gz"

    result = subprocess.run(
        ["bash", str(installer), "--export-seed-data", str(destination)],
        capture_output=True,
        check=False,
        env=installer_environment(tmp_path, "1"),
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert gzip.decompress(destination.read_bytes()).decode() == SEED_CSV
    assert "Exported 1 blacklist rows" in result.stdout


def test_seed_import_runs_before_the_app_and_collector_start() -> None:
    source = INSTALLER.read_text(encoding="utf-8")
    deploy_body = source.split("\ndeploy_services() {", 1)[1].split("\n}", 1)[0]

    assert (
        deploy_body.index("configure-runtime-roles.sh")
        < deploy_body.index("import_seed_data")
        < deploy_body.index("Starting application services")
    )
