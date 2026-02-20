"""Unit tests for app/core/routes/web_routes.py — page routes."""

from unittest.mock import patch, MagicMock
from flask import Flask, Blueprint

import core.routes.web_routes as mod


def make_app():
    """Create test app with web page routes and mocked services."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.extensions["db_service"] = MagicMock()
    app.extensions["collection_service"] = MagicMock()

    bp = Blueprint("web_pages_test", __name__)
    bp.add_url_rule("/", "index", mod.index)
    bp.add_url_rule("/dashboard", "dashboard", mod.dashboard)
    bp.add_url_rule("/search", "blacklist_search", mod.blacklist_search)
    bp.add_url_rule("/data-management", "data_management", mod.data_management)
    bp.add_url_rule("/database-tables", "database_tables", mod.database_tables)
    bp.add_url_rule("/system-logs", "system_logs", mod.system_logs)
    bp.add_url_rule("/dashboard2", "dashboard_page", mod.dashboard_page)
    bp.add_url_rule("/data-table", "data_table", mod.data_table)
    bp.add_url_rule("/test-simple", "test_simple", mod.test_simple)
    bp.add_url_rule("/statistics", "statistics_page", mod.statistics_page)
    bp.add_url_rule("/collection", "collection", mod.collection)
    bp.add_url_rule("/collection-control", "collection_control", mod.collection_control)
    bp.add_url_rule("/regtech-setup", "regtech_setup", mod.regtech_setup)
    bp.add_url_rule("/connection-status", "connection_status", mod.connection_status)
    bp.add_url_rule("/docker/logs", "docker_logs", mod.docker_logs)
    bp.add_url_rule("/data", "data_page", mod.data_page)
    bp.add_url_rule("/debug/routes", "debug_routes", mod.debug_routes)
    bp.add_url_rule("/integrations", "integrations", mod.integrations)
    bp.add_url_rule("/sessions", "sessions", mod.sessions)
    bp.add_url_rule("/collection-logs", "collection_logs", mod.collection_logs)
    app.register_blueprint(bp)

    return app


class TestIndexPage:
    @patch("core.routes.web_routes.render_template", return_value="<html>ok</html>")
    def test_success(self, mock_render):
        app = make_app()
        resp = app.test_client().get("/")
        assert resp.status_code == 200
        mock_render.assert_called_once()

    @patch("core.routes.web_routes.render_template", side_effect=Exception("no template"))
    def test_fallback_to_json(self, mock_render):
        app = make_app()
        resp = app.test_client().get("/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"


class TestDashboard:
    @patch("core.routes.web_routes.render_template", return_value="<html>dash</html>")
    def test_success_with_db(self, mock_render):
        app = make_app()
        mock_db = app.extensions["db_service"]
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.side_effect = [(100,), (80,)]
        mock_cursor.fetchall.return_value = [("REGTECH", 60), ("MANUAL", 20)]
        resp = app.test_client().get("/dashboard")
        assert resp.status_code == 200

    @patch("core.routes.web_routes.render_template", return_value="<html>dash</html>")
    def test_db_query_failure(self, mock_render):
        app = make_app()
        app.extensions["db_service"].get_connection.side_effect = Exception("db")
        resp = app.test_client().get("/dashboard")
        assert resp.status_code == 200

    @patch("core.routes.web_routes.render_template", side_effect=Exception("no tpl"))
    def test_template_error(self, mock_render):
        app = make_app()
        resp = app.test_client().get("/dashboard")
        assert resp.status_code == 500


class TestSimpleTemplateRoutes:
    """Test routes that just render a template with no service dependencies."""

    ROUTES = [
        ("/search", "blacklist_search"),
        ("/data-management", "data_management"),
        ("/database-tables", "database_tables"),
        ("/system-logs", "system_logs"),
        ("/data-table", "data_table"),
        ("/collection-control", "collection_control"),
        ("/regtech-setup", "regtech_setup"),
        ("/connection-status", "connection_status"),
        ("/docker/logs", "docker_logs"),
        ("/data", "data_page"),
        ("/integrations", "integrations"),
        ("/sessions", "sessions"),
        ("/collection-logs", "collection_logs"),
    ]

    @patch("core.routes.web_routes.render_template", return_value="<html>ok</html>")
    def test_all_template_routes_success(self, mock_render):
        app = make_app()
        client = app.test_client()
        for path, _ in self.ROUTES:
            resp = client.get(path)
            assert resp.status_code == 200, f"Failed for {path}"

    @patch("core.routes.web_routes.render_template", side_effect=Exception("tpl error"))
    def test_all_template_routes_error_fallback(self, mock_render):
        app = make_app()
        client = app.test_client()
        for path, _ in self.ROUTES:
            resp = client.get(path)
            assert resp.status_code == 500, f"Expected 500 for {path}"


class TestDashboard2:
    @patch("core.routes.web_routes.render_template", return_value="<html>d2</html>")
    def test_success(self, mock_render):
        app = make_app()
        resp = app.test_client().get("/dashboard2")
        assert resp.status_code == 200

    @patch("core.routes.web_routes.render_template", side_effect=Exception("tpl"))
    def test_error(self, mock_render):
        app = make_app()
        resp = app.test_client().get("/dashboard2")
        assert resp.status_code == 500


class TestStatisticsPage:
    @patch("core.routes.web_routes.render_template", return_value="<html>stats</html>")
    def test_success(self, mock_render):
        app = make_app()
        resp = app.test_client().get("/statistics")
        assert resp.status_code == 200

    @patch("core.routes.web_routes.render_template", side_effect=Exception("tpl"))
    def test_fallback_json(self, mock_render):
        app = make_app()
        resp = app.test_client().get("/statistics")
        assert resp.status_code == 200  # Returns 200 with JSON fallback


class TestCollectionPage:
    @patch("core.routes.web_routes.render_template", return_value="<html>coll</html>")
    def test_success(self, mock_render):
        app = make_app()
        svc = app.extensions["collection_service"]
        svc.get_collection_stats.return_value = {
            "total_collections": 10,
            "success_rate": 95,
            "last_collection_time": "2025-01-01",
            "active_collections": 2,
        }
        svc.get_collection_history.return_value = []
        resp = app.test_client().get("/collection")
        assert resp.status_code == 200

    @patch("core.routes.web_routes.render_template", return_value="<html>coll</html>")
    def test_service_failure_fallback(self, mock_render):
        app = make_app()
        app.extensions["collection_service"].get_collection_stats.side_effect = Exception("fail")
        resp = app.test_client().get("/collection")
        assert resp.status_code == 200  # Falls back with empty data


class TestTestSimple:
    def test_returns_text(self):
        app = make_app()
        resp = app.test_client().get("/test-simple")
        assert resp.status_code == 200
        assert b"TEST WORKING" in resp.data


class TestDebugRoutes:
    def test_returns_route_list(self):
        app = make_app()
        resp = app.test_client().get("/debug/routes")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["total_routes"] > 0
