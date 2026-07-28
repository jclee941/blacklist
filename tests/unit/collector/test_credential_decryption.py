from collections.abc import Generator
from contextlib import contextmanager

import pytest

from collector.config import CollectorConfig
from collector.core.database.service import DatabaseService


class CredentialCursor:
    def __init__(self, row: tuple[object, ...]) -> None:
        self.row: tuple[object, ...] = row

    def execute(self, *_args: object) -> None:
        pass

    def fetchall(self) -> list[tuple[object, ...]]:
        return [self.row]

    def fetchone(self) -> tuple[object, ...]:
        return self.row

    def close(self) -> None:
        pass


class CredentialConnection:
    def __init__(self, row: tuple[object, ...]) -> None:
        self.cursor_instance: CredentialCursor = CredentialCursor(row)

    def cursor(self) -> CredentialCursor:
        return self.cursor_instance

    def close(self) -> None:
        pass


@pytest.fixture(autouse=True)
def reset_credentials_cache() -> Generator[None, None, None]:
    CollectorConfig.clear_credentials_cache()
    yield
    CollectorConfig.clear_credentials_cache()


def encrypted_password() -> str:
    return (
        "Z0FBQUFBQnFhR29pb09JMnEycE92NFFYUl9xdks1SVhHOHE4UEVvTnVEUFZQUTlxMjdidmYyZ0VJd2RjQkFv"
        "VVBiX1hxN2VLMWNudGFzVEo3NzRQZVg5X28yZXRfdllqdzJDMzNJWHRLU2FwdURUaVBhRkVnRExyZ2daUmxReVhK"
        "RlVnX3ZjeXVZOWNHN0trNFB3MjVSeEtYb1FzaTFqZnhqbW55VGRKNVNYV01BS01uMmRRLWVzPQ=="
    )


def test_database_lookup_rejects_wrong_key_without_returning_ciphertext(monkeypatch: pytest.MonkeyPatch) -> None:
    password = encrypted_password()
    monkeypatch.setenv("CREDENTIAL_MASTER_KEY", "wrong-master-key")
    service = DatabaseService()
    config: dict[str, str] = {}
    row: tuple[object, ...] = ("REGTECH", "collector-user", password, True, True, 3600, None, config)

    @contextmanager
    def get_connection() -> Generator[CredentialConnection, None, None]:
        yield CredentialConnection(row)

    service.get_connection = get_connection

    assert service.get_collection_credentials("REGTECH") is None


def test_config_rejects_wrong_key_without_caching_ciphertext(monkeypatch: pytest.MonkeyPatch) -> None:
    password = encrypted_password()
    monkeypatch.setenv("CREDENTIAL_MASTER_KEY", "wrong-master-key")
    config: dict[str, str] = {}
    connection = CredentialConnection(("REGTECH", "collector-user", password, config, True))

    def connect(**_kwargs: object) -> CredentialConnection:
        return connection

    monkeypatch.setattr("collector.config.psycopg2.connect", connect)

    with pytest.raises(ValueError, match="REGTECH credentials not configured"):
        _ = CollectorConfig.get_regtech_credentials()

    assert "REGTECH" not in getattr(CollectorConfig, "_credentials_cache")
