"""Unit tests for blacklist core API routes."""

import pytest
from unittest.mock import Mock, patch
from flask import Flask

from core.errors.handlers import register_error_handlers


class TestBlacklistHealth:
    """Tests for GET /blacklist/health."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True

        @app.before_request
        def set_request_id():
            from flask import g

            g.request_id = "test-req-id"

        from core.routes.api.blacklist.core import blacklist_core_bp

        app.register_blueprint(blacklist_core_bp)
        app.extensions["db_service"] = Mock()
        app.extensions["blacklist_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_health_success(self, client, app):
        """Health returns healthy when DB is up."""
        app.extensions["db_service"].health_check.return_value = True
        response = client.get("/blacklist/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["status"] == "healthy"

    def test_health_db_down(self, client, app):
        """Health returns degraded when DB check fails."""
        app.extensions["db_service"].health_check.return_value = False
        response = client.get("/blacklist/health")
        assert response.status_code == 503

    def test_health_exception(self, client, app):
        """Health handles exception gracefully."""
        app.extensions["db_service"].health_check.side_effect = Exception("timeout")
        response = client.get("/blacklist/health")
        assert response.status_code == 503


class TestBlacklistList:
    """Tests for GET /blacklist/list."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)

        from core.routes.api.blacklist.core import blacklist_core_bp

        app.register_blueprint(blacklist_core_bp)

        mock_db = Mock()
        app.extensions["db_service"] = mock_db
        app.extensions["blacklist_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_list_default_pagination(self, client, app):
        """List returns paginated data with defaults."""

        def mock_query(sql, params=None):
            if "COUNT(*)" in sql:
                return [{"count": 1}]
            return [{"ip": "1.2.3.4"}]

        app.extensions["db_service"].query.side_effect = mock_query
        response = client.get("/blacklist/list")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_list_custom_pagination(self, client, app):
        """List accepts custom page and per_page."""

        def mock_query(sql, params=None):
            if "COUNT(*)" in sql:
                return [{"count": 0}]
            return []

        app.extensions["db_service"].query.side_effect = mock_query
        response = client.get("/blacklist/list?page=2&per_page=50")
        assert response.status_code == 200

    def test_list_invalid_page_zero(self, client, app):
        """Page 0 triggers validation error."""
        response = client.get("/blacklist/list?page=0")
        assert response.status_code == 400

    def test_list_per_page_over_limit(self, client, app):
        """per_page > 1000 triggers validation error."""
        response = client.get("/blacklist/list?per_page=1001")
        assert response.status_code == 400


class TestBlacklistCheck:
    """Tests for POST/GET /blacklist/check."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)

        from core.routes.api.blacklist.core import blacklist_core_bp

        app.register_blueprint(blacklist_core_bp)
        app.extensions["db_service"] = Mock()
        app.extensions["blacklist_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("core.routes.api.blacklist.core.rate_limit", lambda *a, **kw: lambda f: f)
    def test_check_ip_found(self, client, app):
        """Check returns blocked=True for blacklisted IP."""
        app.extensions["blacklist_service"].check_blacklist.return_value = {
            "ip": "1.2.3.4",
            "blocked": True,
            "reason": "malware",
        }
        response = client.post("/blacklist/check", json={"ip": "1.2.3.4"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("core.routes.api.blacklist.core.rate_limit", lambda *a, **kw: lambda f: f)
    def test_check_ip_not_found(self, client, app):
        """Check returns blocked=False for clean IP."""
        app.extensions["blacklist_service"].check_blacklist.return_value = {
            "ip": "8.8.8.8",
            "blocked": False,
            "reason": "clean",
        }
        response = client.post("/blacklist/check", json={"ip": "8.8.8.8"})
        assert response.status_code == 200

    @patch("core.routes.api.blacklist.core.rate_limit", lambda *a, **kw: lambda f: f)
    def test_check_missing_ip(self, client, app):
        """Check without IP returns 400."""
        response = client.post("/blacklist/check", json={})
        assert response.status_code == 400

    @patch("core.routes.api.blacklist.core.rate_limit", lambda *a, **kw: lambda f: f)
    def test_check_invalid_ip_format(self, client, app):
        """Check with invalid IP format returns 400."""
        response = client.post("/blacklist/check", json={"ip": "not-an-ip"})
        assert response.status_code == 400
