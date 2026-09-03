import pytest
from unittest.mock import MagicMock
from datetime import datetime
from flask import Flask, g


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["FORTINET_FEED_TOKEN"] = "unit-feed-token"
    app.config["FORTINET_FEED_ALLOWED_NETWORKS"] = ("203.0.113.0/24",)

    from core.routes.api.fortinet.threat_feed import fortinet_feed_bp
    from core.errors.handlers import register_error_handlers

    app.register_blueprint(fortinet_feed_bp, url_prefix="/api/fortinet")
    register_error_handlers(app)

    app.extensions["db_service"] = MagicMock()

    @app.before_request
    def set_request_id():
        g.request_id = "test-request-id"

    return app


def feed_get(client, path):
    return client.get(
        path,
        headers={"Authorization": "Bearer unit-feed-token"},
        environ_base={"REMOTE_ADDR": "203.0.113.10"},
    )


@pytest.fixture
def app():
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()


class TestThreatFeed:
    def test_threat_feed_requires_token(self, client, app):
        response = client.get(
            "/api/fortinet/threat-feed",
            environ_base={"REMOTE_ADDR": "203.0.113.10"},
        )

        assert response.status_code == 401
        app.extensions["db_service"].query.assert_not_called()

    def test_threat_feed_rejects_source_outside_configured_policy(self, client, app):
        response = client.get(
            "/api/fortinet/threat-feed",
            headers={"Authorization": "Bearer unit-feed-token"},
            environ_base={"REMOTE_ADDR": "198.51.100.10"},
        )

        assert response.status_code == 403
        app.extensions["db_service"].query.assert_not_called()

    def test_threat_feed_json_default(self, client, app):
        app.extensions["db_service"].query.return_value = [
            {"ip_address": "1.2.3.4"},
            {"ip_address": "5.6.7.8"},
        ]
        response = client.get(
            "/api/fortinet/threat-feed",
            headers={"Authorization": "Bearer unit-feed-token"},
            environ_base={"REMOTE_ADDR": "203.0.113.10"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["commands"][0]["command"] == "snapshot"
        assert len(data["commands"][0]["entries"]) == 2
        assert response.headers["X-Total-IPs"] == "2"

    def test_threat_feed_add_command(self, client, app):
        app.extensions["db_service"].query.return_value = [{"ip_address": "1.2.3.4"}]
        response = client.get(
            "/api/fortinet/threat-feed?command=add",
            headers={"Authorization": "Bearer unit-feed-token"},
            environ_base={"REMOTE_ADDR": "203.0.113.10"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["commands"][0]["command"] == "add"

    def test_threat_feed_remove_command(self, client, app):
        app.extensions["db_service"].query.return_value = []
        response = client.get(
            "/api/fortinet/threat-feed?command=remove",
            headers={"Authorization": "Bearer unit-feed-token"},
            environ_base={"REMOTE_ADDR": "203.0.113.10"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["commands"][0]["command"] == "remove"

    def test_threat_feed_text_format(self, client, app):
        app.extensions["db_service"].query.return_value = [
            {"ip_address": "1.2.3.4"},
        ]
        response = client.get(
            "/api/fortinet/threat-feed?format=text",
            headers={"Authorization": "Bearer unit-feed-token"},
            environ_base={"REMOTE_ADDR": "203.0.113.10"},
        )
        assert response.status_code == 200
        assert response.content_type == "text/plain; charset=utf-8"
        assert b"1.2.3.4" in response.data

    def test_threat_feed_invalid_command(self, client, app):
        response = client.get(
            "/api/fortinet/threat-feed?command=invalid",
            headers={"Authorization": "Bearer unit-feed-token"},
            environ_base={"REMOTE_ADDR": "203.0.113.10"},
        )
        assert response.status_code == 400

    def test_threat_feed_invalid_format(self, client, app):
        response = client.get(
            "/api/fortinet/threat-feed?format=xml",
            headers={"Authorization": "Bearer unit-feed-token"},
            environ_base={"REMOTE_ADDR": "203.0.113.10"},
        )
        assert response.status_code == 400

    def test_threat_feed_text_db_error(self, client, app):
        app.extensions["db_service"].query.side_effect = RuntimeError("fail")
        response = client.get(
            "/api/fortinet/threat-feed?format=text",
            headers={"Authorization": "Bearer unit-feed-token"},
            environ_base={"REMOTE_ADDR": "203.0.113.10"},
        )
        assert response.status_code == 500
        assert b"Error" in response.data
        assert b"fail" not in response.data

    def test_threat_feed_json_db_error(self, client, app):
        app.extensions["db_service"].query.side_effect = RuntimeError("fail")
        response = client.get(
            "/api/fortinet/threat-feed?format=json",
            headers={"Authorization": "Bearer unit-feed-token"},
            environ_base={"REMOTE_ADDR": "203.0.113.10"},
        )
        assert response.status_code == 500


class TestJsonConnector:
    def test_json_connector_requires_token(self, client, app):
        response = client.get(
            "/api/fortinet/json-connector",
            environ_base={"REMOTE_ADDR": "203.0.113.10"},
        )

        assert response.status_code == 401

    def test_json_connector_success(self, client, app):
        app.extensions["db_service"].query.side_effect = [
            [
                {
                    "ip_address": "1.2.3.4",
                    "country": "KR",
                    "reason": "malware",
                    "confidence_level": 90,
                    "detection_date": datetime(2026, 1, 1),
                    "updated_at": datetime(2026, 1, 2),
                }
            ],
            [{"count": 50}],
        ]
        response = feed_get(client, "/api/fortinet/json-connector")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]["results"]) == 1
        assert data["data"]["results"][0]["risk_level"] == "high"
        assert data["data"]["metadata"]["total"] == 50

    def test_json_connector_with_limit(self, client, app):
        app.extensions["db_service"].query.side_effect = [
            [
                {
                    "ip_address": "1.2.3.4",
                    "country": "KR",
                    "reason": "scan",
                    "confidence_level": 60,
                    "detection_date": datetime(2026, 1, 1),
                    "updated_at": None,
                }
            ],
            [{"count": 100}],
        ]
        response = feed_get(client, "/api/fortinet/json-connector?limit=10")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["results"][0]["risk_level"] == "medium"

    def test_json_connector_high_risk_filter(self, client, app):
        app.extensions["db_service"].query.side_effect = [
            [],
            [{"count": 0}],
        ]
        response = feed_get(client, "/api/fortinet/json-connector?risk_level=high")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["metadata"]["filters"]["risk_level"] == "high"

    def test_json_connector_country_filter(self, client, app):
        app.extensions["db_service"].query.side_effect = [
            [],
            [{"count": 0}],
        ]
        response = feed_get(client, "/api/fortinet/json-connector?country=kr")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["metadata"]["filters"]["country"] == "KR"

    def test_json_connector_low_risk_classification(self, client, app):
        app.extensions["db_service"].query.side_effect = [
            [
                {
                    "ip_address": "9.8.7.6",
                    "country": None,
                    "reason": None,
                    "confidence_level": 30,
                    "detection_date": None,
                    "updated_at": None,
                }
            ],
            [{"count": 1}],
        ]
        response = feed_get(client, "/api/fortinet/json-connector")
        assert response.status_code == 200
        data = response.get_json()
        result = data["data"]["results"][0]
        assert result["risk_level"] == "low"
        assert result["country"] == "unknown"
        assert result["reason"] == "unspecified"

    def test_json_connector_invalid_limit(self, client, app):
        response = feed_get(client, "/api/fortinet/json-connector?limit=0")
        assert response.status_code == 400

    def test_json_connector_limit_over_10000(self, client, app):
        response = feed_get(client, "/api/fortinet/json-connector?limit=10001")
        assert response.status_code == 400

    def test_json_connector_invalid_risk_level(self, client, app):
        response = feed_get(client, "/api/fortinet/json-connector?risk_level=critical")
        assert response.status_code == 400

    def test_json_connector_db_error(self, client, app):
        app.extensions["db_service"].query.side_effect = Exception("DB error")
        response = feed_get(client, "/api/fortinet/json-connector")
        assert response.status_code == 500
