from unittest.mock import MagicMock
from flask import Flask, Blueprint

import core.routes.web.collection_routes as mod


def make_app():
    """Create a test app with only collection_routes endpoints."""
    app = Flask(__name__, template_folder="/app/templates")
    app.config["TESTING"] = True
    bp = Blueprint("web_test", __name__)
    bp.add_url_rule(
        "/api/collection/<source>/trigger",
        "api_collection_trigger",
        mod.api_collection_trigger,
        methods=["POST"],
    )
    bp.add_url_rule(
        "/api/collection/trigger-all",
        "api_collection_trigger_all",
        mod.api_collection_trigger_all,
        methods=["POST"],
    )
    bp.add_url_rule(
        "/api/collection/stop",
        "api_collection_stop",
        mod.api_collection_stop,
        methods=["POST"],
    )
    bp.add_url_rule(
        "/api/expand-collection-scope",
        "api_expand_collection_scope",
        mod.api_expand_collection_scope,
        methods=["POST"],
    )
    app.register_blueprint(bp)
    return app


class TestCollectionTrigger:
    def test_valid_source_success(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.trigger_collection.return_value = {"success": True, "collected_count": 10}
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/collection/regtech/trigger", json={})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["collected_count"] == 10

    def test_invalid_source(self):
        app = make_app()
        mock_svc = MagicMock()
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/collection/invalid/trigger", json={})

        assert resp.status_code == 400
        assert resp.get_json()["success"] is False

    def test_date_range_regtech(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.trigger_regtech_collection.return_value = {"success": True, "collected_count": 5}
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post(
                "/api/collection/regtech/trigger",
                json={"start_date": "2026-01-01", "end_date": "2026-01-07"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        mock_svc.trigger_regtech_collection.assert_called_once()

    def test_collection_failure(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.trigger_collection.return_value = {"success": False, "error": "timeout"}
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/collection/regtech/trigger", json={})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is False

    def test_exception_returns_500(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.trigger_collection.side_effect = Exception("crash")
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/collection/regtech/trigger", json={})

        assert resp.status_code == 500


class TestTriggerAll:
    def test_success(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.trigger_all_collections.return_value = {
            "success": True,
            "total_collected": 25,
            "results": {"regtech": 25},
        }
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/collection/trigger-all")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["total_collected"] == 25

    def test_failure(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.trigger_all_collections.return_value = {"success": False, "error": "partial fail"}
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/collection/trigger-all")

        assert resp.status_code == 200
        assert resp.get_json()["success"] is False

    def test_exception(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.trigger_all_collections.side_effect = Exception("crash")
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/collection/trigger-all")

        assert resp.status_code == 500


class TestCollectionStop:
    def test_success(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.stop_all_collections.return_value = {"stopped_sources": ["regtech"]}
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/collection/stop")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "regtech" in data["stopped_sources"]

    def test_exception(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.stop_all_collections.side_effect = Exception("crash")
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/collection/stop")

        assert resp.status_code == 500


class TestExpandCollectionScope:
    def test_success(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.expand_collection_scope.return_value = {
            "success": True,
            "message": "expanded",
            "total_collected": 30,
            "sources": ["regtech"],
        }
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/expand-collection-scope")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["total_collected"] == 30

    def test_exception(self):
        app = make_app()
        mock_svc = MagicMock()
        mock_svc.expand_collection_scope.side_effect = Exception("crash")
        app.extensions["collection_service"] = mock_svc

        with app.test_client() as c:
            resp = c.post("/api/expand-collection-scope")

        assert resp.status_code == 500
