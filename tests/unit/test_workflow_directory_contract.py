from pathlib import Path
from typing import Final


ROOT_DIR: Final = Path(__file__).parents[2]
WORKFLOW_DIR: Final = ROOT_DIR / ".github" / "workflows"
WORKFLOW_SUFFIXES: Final = frozenset({".yml", ".yaml"})


def test_workflow_directory_contains_only_action_workflows() -> None:
    # Given: GitHub's workflow discovery directory.
    entries = tuple(WORKFLOW_DIR.iterdir())

    # When: regular files that are not workflow YAML are identified.
    unexpected_files = sorted(
        path.name
        for path in entries
        if path.is_file() and path.suffix not in WORKFLOW_SUFFIXES
    )

    # Then: every regular file is a workflow that actionlint can parse.
    assert unexpected_files == []
