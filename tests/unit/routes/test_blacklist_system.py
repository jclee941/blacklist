import pytest
from unittest.mock import Mock, MagicMock, patch
from flask import Flask

from core.errors.handlers import register_error_handlers


class TestSystemContainers:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)
        from core.routes.api.blacklist.system import blacklist_system_bp

        app.register_blueprint(blacklist_system_bp)
        app.extensions["db_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_containers_status_success(self, client, app):
        """GET /system/containers returns service status"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.get("/system/containers")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "containers" in data
        assert "services" in data
        assert len(data["services"]) == 5  # 5 services
        assert "blacklist-app" in data["services"]
        assert data["services"]["blacklist-app"]["health"] == "healthy"

    def test_containers_db_unhealthy(self, client, app):
        """GET /system/containers with DB check failure marks postgres unhealthy"""
        app.extensions["db_service"].get_connection.side_effect = Exception("DB down")

        response = client.get("/system/containers")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["services"]["blacklist-postgres"]["health"] == "unhealthy"

    def test_containers_no_db_service(self, client, app):
        """GET /system/containers with no db_service extension"""
        del app.extensions["db_service"]

        response = client.get("/system/containers")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


class TestCredentialStatus:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)
        from core.routes.api.blacklist.system import blacklist_system_bp

        app.register_blueprint(blacklist_system_bp)
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch.dict("os.environ", {"REGTECH_ID": "admin123", "REGTECH_PW": "secret456"})
    def test_credential_status_configured(self, client, app):
        """GET /credential/status when credentials are set"""
        response = client.get("/credential/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["status"]["authenticated"] is True
        assert data["status"]["regtech_id"] == "adm*****"  # masked

    @patch.dict("os.environ", {}, clear=True)
    def test_credential_status_not_configured(self, client, app):
        """GET /credential/status when credentials are not set"""
        response = client.get("/credential/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["status"]["authenticated"] is False


class TestRegtechCredentials:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)
        from core.routes.api.blacklist.system import blacklist_system_bp

        app.register_blueprint(blacklist_system_bp)
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch.dict("os.environ", {"REGTECH_ID": "user123", "REGTECH_PW": "pass456"})
    def test_regtech_credentials_configured(self, client, app):
        """GET /credentials/regtech when configured"""
        response = client.get("/credentials/regtech")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["authenticated"] is True
        assert data["configured"] is True

    @patch.dict("os.environ", {}, clear=True)
    def test_regtech_credentials_not_configured(self, client, app):
        """GET /credentials/regtech when not configured"""
        response = client.get("/credentials/regtech")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["authenticated"] is False
        assert data["configured"] is False


class TestDatabaseTables:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)
        from core.routes.api.blacklist.system import blacklist_system_bp

        app.register_blueprint(blacklist_system_bp)
        app.extensions["db_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_database_tables_success(self, client, app):
        """GET /database/tables returns table info"""
        app.extensions["db_service"].show_database_tables.return_value = {
            "success": True,
            "tables": {"blacklist_ips": {"row_count": 1000}},
            "total_tables": 1,
        }

        response = client.get("/database/tables")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["total_tables"] == 1
        assert "blacklist_ips" in data["tables"]

    def test_database_tables_error(self, client, app):
        """GET /database/tables with DB error returns 500"""
        app.extensions["db_service"].show_database_tables.side_effect = Exception("DB error")

        response = client.get("/database/tables")
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
