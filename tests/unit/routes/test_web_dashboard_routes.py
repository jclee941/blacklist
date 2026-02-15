from unittest.mock import patch, MagicMock
from flask import Flask, Blueprint

import core.routes.web.dashboard_routes as mod


def make_app():
    app = Flask(__name__, template_folder="/app/templates")
    app.config["TESTING"] = True
    bp = Blueprint("web_dashboard_test", __name__)
    bp.add_url_rule("/debug/routes", "debug_routes", mod.debug_routes, methods=["GET"])
    bp.add_url_rule("/api/system/logs", "api_system_logs", mod.api_system_logs, methods=["GET"])
    bp.add_url_rule("/api/system/containers", "api_system_containers", mod.api_system_containers, methods=["GET"])
    app.register_blueprint(bp)
    return app


class TestDebugRoutes:
    def test_returns_all_routes(self):
        app = make_app()

        with app.test_client() as c:
            resp = c.get("/debug/routes")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["total_routes"] > 0
        assert isinstance(data["routes"], list)


class TestSystemLogsApi:
    @patch("core.routes.web.dashboard_routes.psutil")
    def test_success(self, mock_psutil):
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.virtual_memory.return_value = MagicMock(percent=60.0)
        mock_psutil.disk_usage.return_value = MagicMock(percent=45.0)

        app = make_app()
        with app.test_client() as c:
            resp = c.get("/api/system/logs")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["logs"]) == 1
        assert data["system_info"]["cpu_percent"] == 25.0

    @patch("core.routes.web.dashboard_routes.psutil")
    def test_error(self, mock_psutil):
        mock_psutil.cpu_percent.side_effect = Exception("no access")

        app = make_app()
        with app.test_client() as c:
            resp = c.get("/api/system/logs")

        assert resp.status_code == 500
        assert resp.get_json()["success"] is False


class TestSystemContainersApi:
    @patch("core.routes.web.dashboard_routes.psutil")
    @patch("core.routes.web.dashboard_routes.os")
    def test_success(self, mock_os, mock_psutil):
        mock_os.getpid.return_value = 1234
        mock_process = MagicMock()
        mock_process.memory_percent.return_value = 10.5
        mock_process.cpu_percent.return_value = 5.0
        mock_process.create_time.return_value = 1700000000.0
        mock_psutil.Process.return_value = mock_process
        mock_psutil.cpu_percent.return_value = 20.0
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.virtual_memory.return_value = MagicMock(percent=50.0, total=8 * 1024**3)
        mock_psutil.disk_usage.return_value = MagicMock(total=100 * 1024**3)

        app = make_app()
        with app.test_client() as c:
            resp = c.get("/api/system/containers")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["containers"]) >= 2
        assert data["system_stats"]["cpu_count"] == 4

    @patch("core.routes.web.dashboard_routes.psutil")
    @patch("core.routes.web.dashboard_routes.os")
    def test_exception(self, mock_os, mock_psutil):
        mock_os.getpid.side_effect = Exception("crash")

        app = make_app()
        with app.test_client() as c:
            resp = c.get("/api/system/containers")

        assert resp.status_code == 500
        assert resp.get_json()["success"] is False
