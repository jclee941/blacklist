from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from core import app_lifecycle


def lease_returning(row, queries: list[str] | None = None):
    recorded: list[str] = queries if queries is not None else []

    @contextmanager
    def lease(_database):
        cursor = MagicMock()
        cursor.fetchone.return_value = row
        cursor.execute.side_effect = lambda sql, *_args: recorded.append(sql)
        connection = MagicMock()
        connection.cursor.return_value = cursor
        yield connection

    return lease


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("REGTECH_ID", "regtech-user")
    monkeypatch.setenv("REGTECH_PW", "regtech-password")
    application = MagicMock()
    application.extensions = {"db_service": object(), "secure_credential_service": MagicMock()}
    return application


def test_env_credentials_are_stored_while_none_are_saved(app, monkeypatch):
    monkeypatch.setattr(app_lifecycle, "connection_lease", lease_returning(None))

    app_lifecycle.seed_regtech_credentials(app)

    app.extensions["secure_credential_service"].save_credentials.assert_called_once_with(
        "REGTECH", "regtech-user", "regtech-password", enabled=True
    )


def test_initdb_placeholder_row_does_not_count_as_saved_credentials(app, monkeypatch):
    # Given: postgres/initdb inserts a REGTECH row whose username and password are empty.
    queries: list[str] = []
    monkeypatch.setattr(app_lifecycle, "connection_lease", lease_returning(None, queries))

    app_lifecycle.seed_regtech_credentials(app)

    # Then: the existence check only matches filled credentials, so the placeholder is replaced.
    assert "COALESCE(username, '') <> ''" in queries[0]
    assert "COALESCE(password, '') <> ''" in queries[0]
    app.extensions["secure_credential_service"].save_credentials.assert_called_once()


def test_saved_credentials_are_never_overwritten(app, monkeypatch):
    monkeypatch.setattr(app_lifecycle, "connection_lease", lease_returning((1,)))

    app_lifecycle.seed_regtech_credentials(app)

    app.extensions["secure_credential_service"].save_credentials.assert_not_called()


@pytest.mark.parametrize("missing", ["REGTECH_ID", "REGTECH_PW"])
def test_incomplete_env_credentials_are_ignored(app, monkeypatch, missing):
    monkeypatch.delenv(missing)
    lease = MagicMock()
    monkeypatch.setattr(app_lifecycle, "connection_lease", lease)

    app_lifecycle.seed_regtech_credentials(app)

    lease.assert_not_called()
    app.extensions["secure_credential_service"].save_credentials.assert_not_called()
