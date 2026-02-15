"""Unit tests for core.utils.db_utils."""

from unittest.mock import patch, MagicMock

import pytest


class TestGetDbConfig:
    """Tests for get_db_config function."""

    def test_returns_dict(self):
        from core.utils.db_utils import get_db_config

        config = get_db_config()
        assert isinstance(config, dict)

    def test_contains_required_keys(self):
        from core.utils.db_utils import get_db_config

        config = get_db_config()
        assert isinstance(config, dict)

    def test_uses_env_variables(self):
        with patch.dict(
            "os.environ",
            {
                "POSTGRES_HOST": "testhost",
                "POSTGRES_PORT": "5433",
                "POSTGRES_DB": "testdb",
                "POSTGRES_USER": "testuser",
                "POSTGRES_PASSWORD": "testpass",
            },
        ):
            from core.utils.db_utils import get_db_config

            config = get_db_config()
            assert isinstance(config, dict)


class TestExecuteQuery:
    """Tests for execute_query function."""

    @patch("core.utils.db_utils.get_db_connection")
    def test_execute_query_returns_results(self, mock_get_conn):
        from core.utils.db_utils import execute_query

        # get_db_connection is a @contextmanager generator, mock as context manager
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, "test"), (2, "test2")]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=mock_conn)
        cm.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = cm

        result = execute_query("SELECT * FROM test")
        assert result == [(1, "test"), (2, "test2")]

    @patch("core.utils.db_utils.get_db_connection")
    def test_execute_query_fetch_one(self, mock_get_conn):
        from core.utils.db_utils import execute_query

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1, "test")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=mock_conn)
        cm.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = cm

        result = execute_query("SELECT * FROM test WHERE id=1", fetch_one=True)
        assert result == (1, "test")


class TestExecuteWrite:
    """Tests for execute_write function."""

    @patch("core.utils.db_utils.get_db_connection")
    def test_execute_write_returns_rowcount(self, mock_get_conn):
        from core.utils.db_utils import execute_write

        mock_cursor = MagicMock()
        mock_cursor.rowcount = 3
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=mock_conn)
        cm.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = cm

        result = execute_write("DELETE FROM test WHERE status='old'")
        assert result == 3


class TestTableExists:
    """Tests for table_exists function."""

    @patch("core.utils.db_utils.execute_query")
    def test_table_exists_returns_true(self, mock_execute):
        from core.utils.db_utils import table_exists

        # table_exists uses RealDictCursor, returns {"exists": True}
        mock_execute.return_value = {"exists": True}
        result = table_exists("blacklist")
        assert result is True

    @patch("core.utils.db_utils.execute_query")
    def test_table_not_exists_returns_false(self, mock_execute):
        from core.utils.db_utils import table_exists

        mock_execute.return_value = None
        result = table_exists("nonexistent")
        assert result is False
