from pathlib import Path

from scripts.offline_bundle import assemble, resolve_version


REPO_ROOT = Path(__file__).parents[2]


def test_bundle_ships_only_application_source_under_source(tmp_path: Path) -> None:
    # Given: operators need source without unrelated repository content.
    bundle = tmp_path / "bundle"

    # When: the deployment bundle is assembled from the current commit.
    assemble(REPO_ROOT, bundle, resolve_version(REPO_ROOT))

    # Then: source/ contains only the tracked application source trees.
    source_dir = bundle / "source"
    assert {path.name for path in source_dir.iterdir()} == {
        "app",
        "collector",
        "frontend",
        "postgres",
    }
    assert (source_dir / "app" / "core" / "app.py").is_file()
    assert (source_dir / "collector" / "run_collector.py").is_file()
    assert (source_dir / "frontend" / "app" / "page.tsx").is_file()
    assert (source_dir / "postgres" / "Dockerfile").is_file()
