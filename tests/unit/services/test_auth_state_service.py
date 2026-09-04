from unittest.mock import MagicMock

import bcrypt
import pytest

from core.services.auth_state_service import AuthStateService, AuthStateUnavailableError


def service_with_cursor() -> tuple[AuthStateService, MagicMock, MagicMock]:
    database = MagicMock()
    connection = MagicMock()
    cursor = MagicMock()
    database.get_connection.return_value = connection
    connection.cursor.return_value = cursor
    return AuthStateService(database), connection, cursor


def test_credentials_fail_closed_when_database_is_unavailable() -> None:
    database = MagicMock()
    database.get_connection.side_effect = RuntimeError("database unavailable")
    service = AuthStateService(database)

    with pytest.raises(AuthStateUnavailableError):
        service.get_credentials("env-admin", "environment-password")


def test_missing_defaults_remain_unconfigured_without_bootstrap() -> None:
    service, connection, cursor = service_with_cursor()
    cursor.fetchall.return_value = []

    credentials = service.get_credentials("", "")

    assert credentials.username == ""
    assert credentials.password_hash == ""
    connection.commit.assert_not_called()


def test_password_rotation_commits_hash_and_generation_together() -> None:
    service, connection, cursor = service_with_cursor()
    current_hash = bcrypt.hashpw(b"current-password", bcrypt.gensalt()).decode()
    cursor.fetchall.return_value = [("admin_password", current_hash)]
    cursor.fetchone.return_value = ("2",)

    rotated = service.rotate_password("admin", "current-password", "replacement-password")

    assert rotated is True
    assert connection.commit.call_count == 1
    parameters = [call.args[1] for call in cursor.execute.call_args_list if len(call.args) > 1]
    assert any("admin_password" in values for values in parameters)
    assert any("admin_session_version" in values for values in parameters)


def test_password_rotation_rolls_back_as_one_unit_when_update_fails() -> None:
    service, connection, cursor = service_with_cursor()
    current_hash = bcrypt.hashpw(b"current-password", bcrypt.gensalt()).decode()
    cursor.fetchall.return_value = [("admin_password", current_hash)]
    cursor.fetchone.return_value = ("2",)
    cursor.execute.side_effect = [None, None, None, RuntimeError("write failed")]

    with pytest.raises(AuthStateUnavailableError):
        service.rotate_password("admin", "current-password", "replacement-password")

    connection.commit.assert_not_called()


def test_missing_session_version_starts_at_zero() -> None:
    service, _connection, cursor = service_with_cursor()
    cursor.fetchone.return_value = None

    assert service.current_session_version("admin") == 0
