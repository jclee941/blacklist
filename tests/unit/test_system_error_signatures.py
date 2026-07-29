from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

from core.exceptions.validation_exceptions import InternalServerError


OPERATIONS = Path(__file__).parents[2] / "app" / "core" / "routes" / "api" / "system" / "operations.py"


def internal_server_error_calls() -> list[ast.Call]:
    tree = ast.parse(OPERATIONS.read_text(encoding="utf-8"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "internal_server_error_cls"
    ]


def test_error_construction_matches_the_exception_signature() -> None:
    # Given: InternalServerError accepts (message, cause) only.
    accepted = set(inspect.signature(InternalServerError.__init__).parameters) - {"self"}
    calls = internal_server_error_calls()
    assert calls, "expected system operations to raise InternalServerError"

    # Then: no call may pass an unsupported keyword. Passing one raises TypeError
    # inside the except block, replacing the real failure with a confusing
    # unhandled exception and masking the original cause.
    for call in calls:
        for keyword in call.keywords:
            assert keyword.arg in accepted, f"line {call.lineno}: unsupported keyword {keyword.arg!r}"


@pytest.mark.parametrize("kwargs", [{"message": "boom"}, {"message": "boom", "cause": "why"}])
def test_supported_signatures_construct(kwargs: dict[str, str]) -> None:
    error = InternalServerError(**kwargs)
    assert error.status_code == 500


def test_unsupported_keyword_is_rejected_by_the_exception() -> None:
    with pytest.raises(TypeError):
        _ = InternalServerError(message="boom", details={"a": 1})  # pyright: ignore[reportCallIssue]


def test_auth_status_calls_a_method_that_exists() -> None:
    # Given: the endpoint reads REGTECH credentials from RegtechConfigService.
    from core.services.regtech_config_service import RegtechConfigService

    source = OPERATIONS.read_text(encoding="utf-8")
    called = set(re.findall(r"regtech_config_service\.(\w+)\(", source))
    assert called, "expected the endpoint to call the credential service"

    # Then: every method it calls must exist. Calling a non-existent method made
    # /api/auth/status return 500 on every request.
    for name in sorted(called):
        assert hasattr(RegtechConfigService, name), f"RegtechConfigService has no {name}()"
