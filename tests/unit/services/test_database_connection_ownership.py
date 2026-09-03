import ast
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from core.services.database_service import DatabaseService


ROOT = Path(__file__).resolve().parents[3]
APP_CORE = ROOT / "app/core"
DIRECT_CHECKOUT_OWNERS = {
    APP_CORE / "services/database_service.py",
    APP_CORE / "services/database_lease.py",
}


def _direct_checkout_lines(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(), filename=str(path))
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get_connection"
    ]


def test_pooled_connections_are_checked_out_only_by_ownership_boundary() -> None:
    # Given
    application_files = [
        path
        for path in APP_CORE.rglob("*.py")
        if path not in DIRECT_CHECKOUT_OWNERS and "database" not in path.relative_to(APP_CORE).parts[:-1]
    ]

    # When
    violations = {
        str(path.relative_to(ROOT)): _direct_checkout_lines(path)
        for path in application_files
        if _direct_checkout_lines(path)
    }

    # Then
    assert violations == {}


def test_stale_pooled_connection_is_closed_through_its_pool() -> None:
    # Given
    with patch.object(DatabaseService, "_initialize_pool_with_retry"):
        service = DatabaseService()
    connection = MagicMock()
    connection_pool = MagicMock()
    connection_pool.putconn.side_effect = [RuntimeError("stale lease"), None]
    service.connection_pool = connection_pool

    # When
    service.return_connection(connection)

    # Then
    assert connection_pool.putconn.call_args_list == [call(connection), call(connection, close=True)]
    connection.close.assert_not_called()
