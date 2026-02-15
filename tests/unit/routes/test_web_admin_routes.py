from unittest.mock import MagicMock, patch
from flask import Flask, Blueprint

import core.routes.web.admin_routes as mod


def make_app():
    app = Flask(__name__, template_folder="/app/templates")
    app.config["TESTING"] = True
    bp = Blueprint("web_admin_test", __name__)
    bp.add_url_rule("/api/credentials/<service_name>", "api_get_credentials", mod.api_get_credentials, methods=["GET"])
    bp.add_url_rule(
        "/api/credentials/<service_name>", "api_delete_credentials", mod.api_delete_credentials, methods=["DELETE"]
    )
    bp.add_url_rule("/api/database/tables", "api_database_tables", mod.api_database_tables, methods=["GET"])
    bp.add_url_rule("/api/database/clear", "api_clear_database", mod.api_clear_database, methods=["POST"])
    bp.add_url_rule(
        "/api/admin/regtech/test-connection",
        "api_admin_regtech_test_connection",
        mod.api_admin_regtech_test_connection,
        methods=["POST"],
    )
    bp.add_url_rule(
        "/api/admin/regtech/credentials",
        "api_admin_get_regtech_credentials",
        mod.api_admin_get_regtech_credentials,
        methods=["GET"],
    )
    app.register_blueprint(bp)
    return app


class TestGetCredentials:
    def test_success(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_collection_credentials.return_value = {
            "service_name": "REGTECH",
            "username": "admin",
            "is_authenticated": True,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-02",
        }
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/api/credentials/regtech")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["username"] == "admin"
        assert data["is_authenticated"] is True

    def test_db_error_in_result(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_collection_credentials.return_value = {"error": "table not found"}
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/api/credentials/regtech")

        assert resp.status_code == 500
        assert resp.get_json()["success"] is False

    def test_exception(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_collection_credentials.side_effect = Exception("db down")
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/api/credentials/regtech")

        assert resp.status_code == 500


class TestDeleteCredentials:
    def test_success(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.delete_collection_credentials.return_value = {"success": True}
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.delete("/api/credentials/regtech")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "REGTECH" in data["message"]

    def test_failure(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.delete_collection_credentials.return_value = {"success": False, "error": "not found"}
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.delete("/api/credentials/regtech")

        assert resp.status_code == 200
        assert resp.get_json()["success"] is False

    def test_exception(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.delete_collection_credentials.side_effect = Exception("db down")
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.delete("/api/credentials/regtech")

        assert resp.status_code == 500


class TestDatabaseTables:
    def test_success(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.show_database_tables.return_value = {"tables": ["blacklist", "collection_history"], "count": 2}
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/api/database/tables")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["count"] == 2

    def test_exception(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.show_database_tables.side_effect = Exception("query fail")
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/api/database/tables")

        assert resp.status_code == 500


class TestClearDatabase:
    def test_success(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.clear_all_blacklist_data.return_value = {"success": True, "deleted": 100}
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.post("/api/database/clear")

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_exception(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.clear_all_blacklist_data.side_effect = Exception("crash")
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.post("/api/database/clear")

        assert resp.status_code == 500


class TestRegtechTestConnection:
    def test_success_triggers_collection(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.test_regtech_connection.return_value = {"success": True}
        mock_svc.trigger_regtech_collection.return_value = {"success": True, "count": 5}
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/admin/regtech/test-connection")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["auto_collection_started"] is True

    def test_connection_failure(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.test_regtech_connection.return_value = {"success": False, "error": "timeout"}
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/admin/regtech/test-connection")

        assert resp.status_code == 200
        assert resp.get_json()["success"] is False

    def test_exception(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.test_regtech_connection.side_effect = Exception("crash")
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/admin/regtech/test-connection")

        assert resp.status_code == 500


class TestRegtechAdminGetCredentials:
    @patch("core.services.regtech_config_service.RegtechConfigService")
    def test_with_credentials(self, mock_cls):
        mock_svc = MagicMock()
        mock_svc.get_regtech_credentials.return_value = {
            "username": "admin",
            "password": "secret",
            "base_url": "https://regtech.fsec.or.kr",
        }
        mock_cls.return_value = mock_svc

        app = make_app()
        with app.test_client() as c:
            resp = c.get("/api/admin/regtech/credentials")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["has_credentials"] is True
        assert data["data"]["username"] == "admin"

    @patch("core.services.regtech_config_service.RegtechConfigService")
    def test_no_credentials(self, mock_cls):
        mock_svc = MagicMock()
        mock_svc.get_regtech_credentials.return_value = None
        mock_cls.return_value = mock_svc

        app = make_app()
        with app.test_client() as c:
            resp = c.get("/api/admin/regtech/credentials")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["has_credentials"] is False

    @patch("core.services.regtech_config_service.RegtechConfigService")
    def test_exception(self, mock_cls):
        mock_cls.side_effect = Exception("import error")

        app = make_app()
        with app.test_client() as c:
            resp = c.get("/api/admin/regtech/credentials")

        assert resp.status_code == 500
