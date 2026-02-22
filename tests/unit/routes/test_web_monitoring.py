from unittest.mock import MagicMock, patch
from flask import Flask

from core.routes.web.monitoring import monitoring_dashboard_bp


def make_app():
    app = Flask(__name__, template_folder="/app/templates")
    app.config["TESTING"] = True
    app.register_blueprint(monitoring_dashboard_bp)
    return app


class TestDashboardDataApi:
    @patch("core.routes.web.monitoring.datetime")
    def test_success(self, mock_dt):
        mock_dt.now.return_value.isoformat.return_value = "2026-01-01T00:00:00"
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_dashboard_stats.return_value = {
            "total_count": 100,
            "regtech_count": 50,
            "last_updated": "2026-01-01",
        }
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/api/dashboard-data")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["total_ips"] == 100
        assert data["regtech_count"] == 50

    def test_error_returns_500(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_dashboard_stats.side_effect = Exception("db error")
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/api/dashboard-data")

        assert resp.status_code == 500
        data = resp.get_json()
        assert data["success"] is False

    def test_alternate_url(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_dashboard_stats.return_value = {"total_count": 0, "regtech_count": 0}
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/dashboard/api/dashboard-data")

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


class TestMonitoringDashboard:
    @patch.dict("os.environ", {"VERSION": "2.0.0"})
    @patch("core.routes.web.monitoring.render_template")
    def test_success(self, mock_render):
        mock_render.return_value = "<html>dashboard</html>"
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_blacklist_stats.return_value = {
            "total_ips": 100,
            "active_ips": 50,
            "last_update": "2026-01-01",
        }
        mock_coll = MagicMock()
        mock_coll.get_collection_stats.return_value = {"total_collections": 10}
        app.extensions["db_service"] = mock_db
        app.extensions["collection_service"] = mock_coll

        with app.test_client() as c:
            resp = c.get("/monitoring")

        assert resp.status_code == 200
        mock_render.assert_called_once_with(
            "monitoring/dashboard.html",
            total_ips=100,
            active_ips=50,
            last_update="2026-01-01",
            collection_count=10,
            version="2.0.0",
        )

    @patch("core.routes.web.monitoring.render_template")
    def test_dashboard_url(self, mock_render):
        mock_render.return_value = "<html>dashboard</html>"
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_blacklist_stats.return_value = {"total_ips": 0, "active_ips": 0}
        mock_coll = MagicMock()
        mock_coll.get_collection_stats.return_value = {"total_collections": 0}
        app.extensions["db_service"] = mock_db
        app.extensions["collection_service"] = mock_coll

        with app.test_client() as c:
            resp = c.get("/dashboard")

        assert resp.status_code == 200

    @patch.dict("os.environ", {"VERSION": "2.0.0"})
    @patch("core.routes.web.monitoring.render_template")
    def test_exception_fallback(self, mock_render):
        mock_render.return_value = "<html>fallback</html>"
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_blacklist_stats.side_effect = Exception("db error")
        mock_coll = MagicMock()
        app.extensions["db_service"] = mock_db
        app.extensions["collection_service"] = mock_coll

        with app.test_client() as c:
            resp = c.get("/monitoring")

        assert resp.status_code == 200
        mock_render.assert_called_once_with(
            "monitoring/dashboard.html",
            total_ips=0,
            active_ips=0,
            last_update="없음",
            collection_count=0,
            version="2.0.0",
        )
