import pytest
from unittest.mock import Mock, MagicMock, patch
from flask import Flask, g

from core.errors.handlers import register_error_handlers


def make_app():
    """Create test app with database API blueprint"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_error_handlers(app)
    from core.routes.api.database_api import database_api_bp

    app.register_blueprint(database_api_bp)
    app.extensions["db_service"] = Mock()

    @app.before_request
    def set_request_id():
        g.request_id = "test-request-id"

    return app


class TestConnectionStatus:
    @pytest.fixture
    def app(self):
        return make_app()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_connection_status_success(self, client, app):
        """GET /database/connection returns pool status"""
        app.extensions["db_service"].get_connection_status.return_value = {
            "connected": True,
            "pool_size": 10,
            "pool_used": 2,
        }

        response = client.get("/database/connection")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["connected"] is True
        assert data["data"]["pool_size"] == 10

    def test_connection_status_error(self, client, app):
        """GET /database/connection with error raises DatabaseError (500)"""
        app.extensions["db_service"].get_connection_status.side_effect = Exception("Pool error")

        response = client.get("/database/connection")
        assert response.status_code == 500


class TestDatabaseSchema:
    @pytest.fixture
    def app(self):
        return make_app()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_schema_success(self, client, app):
        """GET /database/schema returns table list"""
        app.extensions["db_service"].query.return_value = [
            {"name": "blacklist_ips", "column_count": 10, "row_count": 5000},
            {"name": "whitelist_ips", "column_count": 8, "row_count": 100},
        ]

        response = client.get("/database/schema")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["total"] == 2
        assert len(data["data"]["tables"]) == 2

    def test_schema_db_error(self, client, app):
        """GET /database/schema with DB error returns 500"""
        app.extensions["db_service"].query.side_effect = Exception("Query failed")

        response = client.get("/database/schema")
        assert response.status_code == 500


class TestTableData:
    @pytest.fixture
    def app(self):
        return make_app()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_table_data_allowed_table(self, client, app):
        """GET /database/table/blacklist_ips returns data"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"total": 100}
        mock_cursor.fetchall.side_effect = [
            [{"column_name": "id"}, {"column_name": "ip_address"}],
            [{"id": 1, "ip_address": "10.0.0.1"}],
        ]
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.get("/database/table/blacklist_ips")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["table_name"] == "blacklist_ips"

    def test_table_data_disallowed_table(self, client, app):
        """GET /database/table/users returns 400 (not in whitelist)"""
        response = client.get("/database/table/users")
        assert response.status_code == 400
        data = response.get_json()
        assert "not allowed" in data.get("message", data.get("detail", "")).lower()

    def test_table_data_invalid_page(self, client, app):
        """GET /database/table/blacklist_ips?page=abc returns 400"""
        response = client.get("/database/table/blacklist_ips?page=abc")
        assert response.status_code == 400

    def test_table_data_page_zero(self, client, app):
        """GET /database/table/blacklist_ips?page=0 returns 400"""
        response = client.get("/database/table/blacklist_ips?page=0")
        assert response.status_code == 400

    def test_table_data_limit_too_large(self, client, app):
        """GET /database/table/blacklist_ips?limit=5000 returns 400"""
        response = client.get("/database/table/blacklist_ips?limit=5000")
        assert response.status_code == 400

    def test_table_data_limit_zero(self, client, app):
        """GET /database/table/blacklist_ips?limit=0 returns 400"""
        response = client.get("/database/table/blacklist_ips?limit=0")
        assert response.status_code == 400


class TestColumnStats:
    @pytest.fixture
    def app(self):
        return make_app()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_column_stats_success(self, client, app):
        """GET /database/table/blacklist_ips/column/ip_address returns stats"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {
            "total_rows": 5000,
            "non_null_count": 4999,
            "distinct_count": 4500,
        }
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.get("/database/table/blacklist_ips/column/ip_address")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["table_name"] == "blacklist_ips"
        assert data["data"]["column_name"] == "ip_address"
        assert data["data"]["stats"]["total_rows"] == 5000

    def test_column_stats_disallowed_table(self, client, app):
        """GET /database/table/secret_table/column/id returns 400"""
        response = client.get("/database/table/secret_table/column/id")
        assert response.status_code == 400

    def test_column_stats_db_error(self, client, app):
        """GET /database/table/blacklist_ips/column/bad_col with DB error returns 500"""
        app.extensions["db_service"].get_connection.side_effect = Exception("DB error")

        response = client.get("/database/table/blacklist_ips/column/bad_col")
        assert response.status_code == 500
