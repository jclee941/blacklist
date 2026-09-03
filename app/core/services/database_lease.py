from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol

from psycopg2.extensions import connection as PostgreSQLConnection


class PooledConnectionOwner(Protocol):
    def get_connection(self) -> PostgreSQLConnection: ...

    def return_connection(self, connection: PostgreSQLConnection) -> None: ...


@contextmanager
def connection_lease(owner: PooledConnectionOwner) -> Iterator[PostgreSQLConnection]:
    connection = owner.get_connection()
    try:
        yield connection
    finally:
        try:
            connection.rollback()
        finally:
            owner.return_connection(connection)
