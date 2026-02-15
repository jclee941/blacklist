import pytest
from unittest.mock import Mock, MagicMock, patch
from flask import Flask

from core.errors.handlers import register_error_handlers


class TestManualAddIP:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)
        from core.routes.api.blacklist.management import blacklist_management_bp

        app.register_blueprint(blacklist_management_bp)
        app.extensions["db_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_manual_add_success(self, client, app):
        """POST /blacklist/manual-add with valid data"""
        app.extensions["db_service"].query.return_value = [{"count": 0}]
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.post(
            "/blacklist/manual-add",
            json={"ip_address": "10.0.0.1", "country": "KR", "notes": "test"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["ip_address"] == "10.0.0.1"
        assert data["data"]["source"] == "MANUAL"
        assert data["data"]["country"] == "KR"

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_manual_add_missing_ip(self, client, app):
        """POST /blacklist/manual-add with empty ip_address"""
        response = client.post("/blacklist/manual-add", json={"ip_address": ""})
        assert response.status_code == 400

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_manual_add_no_body(self, client, app):
        """POST /blacklist/manual-add with no JSON body"""
        response = client.post("/blacklist/manual-add", json={})
        assert response.status_code == 400

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_manual_add_invalid_ip_format(self, client, app):
        """POST /blacklist/manual-add with bad IP format"""
        response = client.post("/blacklist/manual-add", json={"ip_address": "not-an-ip"})
        assert response.status_code == 400

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_manual_add_ip_range_invalid(self, client, app):
        """POST /blacklist/manual-add with octets > 255"""
        response = client.post("/blacklist/manual-add", json={"ip_address": "999.999.999.999"})
        assert response.status_code == 400

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_manual_add_duplicate_ip(self, client, app):
        """POST /blacklist/manual-add with existing IP returns 409"""
        app.extensions["db_service"].query.return_value = [{"count": 1}]

        response = client.post("/blacklist/manual-add", json={"ip_address": "10.0.0.1"})
        assert response.status_code == 409

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_manual_add_default_country(self, client, app):
        """POST /blacklist/manual-add defaults country to UNKNOWN"""
        app.extensions["db_service"].query.return_value = [{"count": 0}]
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.post("/blacklist/manual-add", json={"ip_address": "10.0.0.2"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["country"] == "UNKNOWN"


class TestManualRemoveIP:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)
        from core.routes.api.blacklist.management import blacklist_management_bp

        app.register_blueprint(blacklist_management_bp)
        app.extensions["db_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_remove_success(self, client, app):
        """DELETE /blacklist/remove/<ip> with existing IP"""
        app.extensions["db_service"].query.return_value = [{"count": 1}]
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.delete("/blacklist/remove/10.0.0.1")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["ip_address"] == "10.0.0.1"

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_remove_invalid_ip(self, client, app):
        """DELETE /blacklist/remove/<ip> with bad IP format"""
        response = client.delete("/blacklist/remove/not-an-ip")
        assert response.status_code == 400

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_remove_not_found(self, client, app):
        """DELETE /blacklist/remove/<ip> when IP not in blacklist"""
        app.extensions["db_service"].query.return_value = [{"count": 0}]

        response = client.delete("/blacklist/remove/10.0.0.1")
        assert response.status_code == 404


class TestWhitelistManualAdd:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)
        from core.routes.api.blacklist.management import blacklist_management_bp

        app.register_blueprint(blacklist_management_bp)
        app.extensions["db_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_whitelist_add_success(self, client, app):
        """POST /whitelist/manual-add with valid data"""
        app.extensions["db_service"].query.return_value = [{"count": 0}]
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.post(
            "/whitelist/manual-add",
            json={"ip_address": "192.168.1.1", "country": "US", "reason": "trusted"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["ip_address"] == "192.168.1.1"
        assert data["data"]["source"] == "MANUAL"

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_whitelist_add_missing_ip(self, client, app):
        """POST /whitelist/manual-add with empty ip_address"""
        response = client.post("/whitelist/manual-add", json={"ip_address": ""})
        assert response.status_code == 400

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_whitelist_add_duplicate(self, client, app):
        """POST /whitelist/manual-add with existing IP returns 409"""
        app.extensions["db_service"].query.return_value = [{"count": 1}]

        response = client.post("/whitelist/manual-add", json={"ip_address": "192.168.1.1"})
        assert response.status_code == 409

    @patch("core.routes.api.blacklist.management.rate_limit", lambda *a, **kw: lambda f: f)
    def test_whitelist_add_invalid_ip(self, client, app):
        """POST /whitelist/manual-add with bad IP"""
        response = client.post("/whitelist/manual-add", json={"ip_address": "abc.def.ghi.jkl"})
        assert response.status_code == 400


class TestWhitelistList:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)
        from core.routes.api.blacklist.management import blacklist_management_bp

        app.register_blueprint(blacklist_management_bp)
        app.extensions["db_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_whitelist_list_success(self, client, app):
        """GET /whitelist/list returns paginated data"""
        app.extensions["db_service"].query.side_effect = [
            [{"id": 1, "ip_address": "192.168.1.1"}],
            [{"count": 1}],
        ]

        response = client.get("/whitelist/list")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 50

    def test_whitelist_list_with_pagination(self, client, app):
        """GET /whitelist/list?page=2&per_page=10"""
        app.extensions["db_service"].query.side_effect = [
            [],
            [{"count": 25}],
        ]

        response = client.get("/whitelist/list?page=2&per_page=10")
        assert response.status_code == 200
        data = response.get_json()
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["per_page"] == 10
        assert data["pagination"]["total"] == 25
        assert data["pagination"]["pages"] == 3  # ceil(25/10)

    def test_whitelist_list_db_error(self, client, app):
        """GET /whitelist/list with DB error returns 500"""
        app.extensions["db_service"].query.side_effect = Exception("DB down")

        response = client.get("/whitelist/list")
        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
