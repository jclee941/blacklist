import re
from pathlib import Path
from typing import Final


ROOT_DIR: Final = Path(__file__).parents[2]
AUTO_MERGE_WORKFLOW: Final = (
    ROOT_DIR / ".github" / "workflows" / "13_pr-auto-merge.yml"
)
AUTO_MERGE_QUERY_FIELDS: Final = frozenset(
    {"author", "isDraft", "reviewDecision", "state", "url"}
)
JSON_FIELDS_PATTERN: Final = re.compile(r"--json\s+([A-Za-z,]+)")


def test_auto_merge_queries_only_metadata_used_by_the_workflow() -> None:
    # Given: the metadata query in the auto-merge workflow.
    workflow = AUTO_MERGE_WORKFLOW.read_text(encoding="utf-8")
    fields_match = JSON_FIELDS_PATTERN.search(workflow)
    assert fields_match is not None

    # When: its requested GraphQL fields are parsed.
    requested_fields = frozenset(fields_match.group(1).split(","))

    # Then: the query requests only fields consumed by the workflow guardrails.
    assert requested_fields == AUTO_MERGE_QUERY_FIELDS
