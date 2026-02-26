"""Tests for app/core/routes/api/blacklist/collection.py — REGTECH collection trigger via collector."""

from unittest.mock import patch, MagicMock
from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    with patch("core.utils.rate_limit.rate_limit", lambda *a, **kw: lambda f: f):
        from core.routes.api.blacklist.collection import blacklist_collection_bp

        app.register_blueprint(blacklist_collection_bp, url_prefix="/api")

    return app


class TestTriggerRegtechCollection:
    """POST /api/collection/regtech/trigger"""

    def setup_method(self):
        self.app = create_app()
        self.client = self.app.test_client()

    @patch("requests.post")
    def test_trigger_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.post(
                "/api/collection/regtech/trigger",
                json={"start_date": "2025-01-01", "end_date": "2025-01-31"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "timestamp" in data

    @patch("requests.post")
    def test_trigger_collector_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.post("/api/collection/regtech/trigger", json={})

        assert resp.status_code == 502
        data = resp.get_json()
        assert data["success"] is False

    @patch("requests.post")
    def test_trigger_connection_error(self, mock_post):
        import requests as real_requests

        mock_post.side_effect = real_requests.exceptions.ConnectionError("refused")

        with self.app.app_context():
            resp = self.client.post("/api/collection/regtech/trigger", json={})

        assert resp.status_code == 500
        data = resp.get_json()
        assert data["success"] is False

    @patch("requests.post")
    def test_trigger_empty_json_body(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.post(
                "/api/collection/regtech/trigger",
                json={},
            )

        assert resp.status_code == 200

    @patch.dict("os.environ", {"COLLECTOR_URL": "http://custom-collector:9999"})
    @patch("requests.post")
    def test_trigger_uses_env_collector_url(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.post("/api/collection/regtech/trigger", json={})

        assert resp.status_code == 200
        call_url = mock_post.call_args[0][0]
        assert "custom-collector:9999" in call_url

    @patch("requests.post")
    def test_trigger_passes_dates_to_collector(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        with self.app.app_context():
            self.client.post(
                "/api/collection/regtech/trigger",
                json={"start_date": "2025-06-01", "end_date": "2025-06-30"},
            )

        call_kwargs = mock_post.call_args
        sent_json = call_kwargs[1].get("json") or call_kwargs.kwargs.get("json")
        assert sent_json["start_date"] == "2025-06-01"
        assert sent_json["end_date"] == "2025-06-30"
