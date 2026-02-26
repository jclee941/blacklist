"""Extended tests for database_service.py - covers uncovered methods."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


class TestDatabaseServiceExtended:
    """Additional tests for DatabaseService methods not covered in base tests."""

    def _make_service(self):
        with patch.object(
            __import__("core.services.database_service", fromlist=["DatabaseService"]).DatabaseService,
            "_initialize_pool_with_retry",
        ):
            from core.services.database_service import DatabaseService

            svc = DatabaseService()
        svc.db_config = {"host": "localhost", "port": 5432, "database": "test_db"}
        return svc

    def _mock_conn(self, svc):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        svc.get_connection = Mock(return_value=mock_conn)
        svc.return_connection = Mock()
        return mock_conn, mock_cursor

    # ---- close_all_connections ----

    def test_close_all_connections_success(self):
        svc = self._make_service()
        mock_pool = MagicMock()
        svc.connection_pool = mock_pool
        svc.close_all_connections()
        mock_pool.closeall.assert_called_once()
        assert svc.connection_pool is None

    def test_close_all_connections_no_pool(self):
        svc = self._make_service()
        svc.connection_pool = None
        svc.close_all_connections()

    def test_close_all_connections_exception(self):
        svc = self._make_service()
        mock_pool = MagicMock()
        mock_pool.closeall.side_effect = Exception("pool error")
        svc.connection_pool = mock_pool
        svc.close_all_connections()

    # ---- health_check ----

    def test_health_check_success(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.fetchone.return_value = (1,)
        assert svc.health_check() is True

    def test_health_check_failure(self):
        svc = self._make_service()
        svc.get_connection = Mock(side_effect=Exception("connection error"))
        assert svc.health_check() is False

    # ---- get_connection_status ----

    def test_get_connection_status_healthy(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.fetchone.return_value = (1,)
        svc.connection_pool = MagicMock()
        svc.connection_pool.minconn = 1
        svc.connection_pool.maxconn = 10
        result = svc.get_connection_status()
        assert result["status"] == "healthy"

    def test_get_connection_status_unhealthy(self):
        svc = self._make_service()
        svc.get_connection = Mock(side_effect=Exception("conn error"))
        svc.connection_pool = MagicMock()
        svc.connection_pool.minconn = 1
        svc.connection_pool.maxconn = 10
        result = svc.get_connection_status()
        assert result["status"] == "unhealthy"

    def test_get_connection_status_exception(self):
        svc = self._make_service()
        svc.get_connection = Mock(side_effect=Exception("fail"))
        svc.connection_pool = None
        result = svc.get_connection_status()
        assert result["status"] in ("error", "unhealthy")

    # ---- execute success path ----

    def test_execute_success(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.rowcount = 5
        result = svc.execute("UPDATE test SET x=1")
        assert result == 5
        mock_conn.commit.assert_called_once()

    def test_execute_with_params(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.rowcount = 1
        result = svc.execute("UPDATE test SET x=%s WHERE id=%s", (1, 2))
        assert result == 1

    # ---- query paths ----

    def test_query_without_params(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
        result = svc.query("SELECT * FROM test")
        assert len(result) == 2

    def test_query_with_params(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.fetchall.return_value = [{"id": 1}]
        result = svc.query("SELECT * FROM test WHERE id=%s", (1,))
        assert len(result) == 1

    def test_query_empty(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.fetchall.return_value = []
        result = svc.query("SELECT * FROM test")
        assert result == []

    # ---- create_raw_connection ----

    @patch("core.services.database_service.psycopg2")
    def test_create_raw_connection_success(self, mock_psycopg2):
        svc = self._make_service()
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        result = svc.create_raw_connection()
        assert result == mock_conn

    @patch("core.services.database_service.psycopg2")
    def test_create_raw_connection_failure(self, mock_psycopg2):
        svc = self._make_service()
        mock_psycopg2.connect.side_effect = Exception("connection refused")
        with pytest.raises(Exception):
            svc.create_raw_connection()

    # ---- save_blacklist_ip ----

    def test_save_blacklist_ip_success(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        ip_data = {
            "ip_address": "1.1.1.1",
            "reason": "malware",
            "source": "REGTECH",
            "category": "threat",
            "country": "KR",
            "confidence_score": 95,
            "detection_date": "2024-01-01",
            "removal_date": None,
            "is_active": True,
        }
        result = svc.save_blacklist_ip(ip_data)
        assert result is True
        mock_conn.commit.assert_called_once()

    def test_save_blacklist_ip_exception(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.execute.side_effect = Exception("constraint violation")
        result = svc.save_blacklist_ip({"ip_address": "1.1.1.1"})
        assert result is False
        mock_conn.rollback.assert_called_once()

    # ---- get_collection_credentials ----

    def test_get_collection_credentials_from_secure_svc(self):
        svc = self._make_service()
        mock_secure = MagicMock()
        mock_secure.get_credentials.return_value = {
            "username": "user1",
            "password": "pass1",
            "config": "{}",
        }
        from flask import Flask

        app = Flask(__name__)
        app.extensions["secure_credential_service"] = mock_secure
        with app.app_context():
            result = svc.get_collection_credentials("regtech")
        assert result["username"] == "user1"

    def test_get_collection_credentials_from_db(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.fetchone.return_value = ("regtech", "user1", "pass1", "{}", datetime.now(), datetime.now())
        mock_secure = MagicMock()
        mock_secure.get_credentials.return_value = None
        from flask import Flask

        app = Flask(__name__)
        app.extensions["secure_credential_service"] = mock_secure
        with app.app_context():
            result = svc.get_collection_credentials("regtech")
        assert result["username"] == "user1"

    def test_get_collection_credentials_not_found(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.fetchone.return_value = None
        mock_secure = MagicMock()
        mock_secure.get_credentials.return_value = None
        from flask import Flask

        app = Flask(__name__)
        app.extensions["secure_credential_service"] = mock_secure
        with app.app_context():
            result = svc.get_collection_credentials("regtech")
        assert "warning" in result or result.get("username") is None

    # ---- show_database_tables ----

    def test_show_database_tables_success(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.fetchall.side_effect = [
            [("blacklist_ips",), ("whitelist_ips",)],
            [("id", "integer"), ("ip_address", "varchar")],
            [("id", "integer")],
        ]
        mock_cursor.fetchone.side_effect = [(100,), (50,)]
        result = svc.show_database_tables()
        assert result["success"] is True

    def test_show_database_tables_exception(self):
        svc = self._make_service()
        svc.get_connection = Mock(side_effect=Exception("db error"))
        result = svc.show_database_tables()
        assert result.get("success") is False or "error" in result

    # ---- get_blacklist_stats ----

    def test_get_blacklist_stats_success(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.fetchone.side_effect = [
            (100,),
            (50,),
            (datetime(2024, 1, 15, 10, 30),),
        ]
        result = svc.get_blacklist_stats()
        assert result["total_ips"] == 100
        assert result["active_ips"] == 50
        assert "2024" in result["last_update"]

    def test_get_blacklist_stats_no_last_update(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.fetchone.side_effect = [
            (0,),
            (0,),
            (None,),
        ]
        result = svc.get_blacklist_stats()
        assert result["total_ips"] == 0
        assert result["last_update"] == "없음"

    def test_get_blacklist_stats_exception(self):
        svc = self._make_service()
        svc.get_connection = Mock(side_effect=Exception("db error"))
        result = svc.get_blacklist_stats()
        assert result["total_ips"] == 0
        assert result["last_update"] == "오류"

    # ---- get_dashboard_stats ----

    def test_get_dashboard_stats_success(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.fetchone.side_effect = [
            (200,),
            (150,),
            (datetime(2024, 6, 15, 14, 0),),
        ]
        result = svc.get_dashboard_stats()
        assert result["total_count"] == 200
        assert result["regtech_count"] == 150
        assert "2024" in result["last_updated"]

    def test_get_dashboard_stats_no_last_collection(self):
        svc = self._make_service()
        mock_conn, mock_cursor = self._mock_conn(svc)
        mock_cursor.fetchone.side_effect = [
            (0,),
            (0,),
            (None,),
        ]
        result = svc.get_dashboard_stats()
        assert result["total_count"] == 0
        assert result["last_updated"] == "확인 중..."

    def test_get_dashboard_stats_exception(self):
        svc = self._make_service()
        svc.get_connection = Mock(side_effect=Exception("db error"))
        result = svc.get_dashboard_stats()
        assert result["total_count"] == 0
        assert result["last_updated"] == "오류"
