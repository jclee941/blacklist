import pytest
from unittest.mock import Mock, MagicMock, patch
from flask import Flask

from core.errors.handlers import register_error_handlers


class TestBatchAdd:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)
        from core.routes.api.blacklist.batch import blacklist_batch_bp

        app.register_blueprint(blacklist_batch_bp)
        mock_db = Mock()
        app.extensions["db_service"] = mock_db
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("core.routes.api.blacklist.batch.rate_limit", lambda *a, **kw: lambda f: f)
    def test_batch_add_success(self, client, app):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.post(
            "/blacklist/batch/add",
            json={
                "ips": ["1.2.3.4", "5.6.7.8"],
                "reason": "test",
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["summary"]["total_requested"] == 2

    @patch("core.routes.api.blacklist.batch.rate_limit", lambda *a, **kw: lambda f: f)
    def test_batch_add_uses_blacklist_composite_conflict_target(self, client, app):
        # Given
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        app.extensions["db_service"].get_connection.return_value = mock_conn

        # When
        response = client.post("/blacklist/batch/add", json={"ips": ["192.0.2.1"]})

        # Then
        assert response.status_code == 200
        insert_query = mock_cursor.execute.call_args.args[0]
        assert "ON CONFLICT (ip_address, source)" in insert_query

    @patch("core.routes.api.blacklist.batch.rate_limit", lambda *a, **kw: lambda f: f)
    def test_batch_add_empty_list(self, client, app):
        response = client.post("/blacklist/batch/add", json={"ips": []})
        assert response.status_code == 400

    @patch("core.routes.api.blacklist.batch.rate_limit", lambda *a, **kw: lambda f: f)
    def test_batch_add_no_ips_key(self, client, app):
        response = client.post("/blacklist/batch/add", json={})
        assert response.status_code == 400

    @patch("core.routes.api.blacklist.batch.rate_limit", lambda *a, **kw: lambda f: f)
    def test_batch_add_invalid_ips_rejected(self, client, app):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.post(
            "/blacklist/batch/add",
            json={
                "ips": ["1.2.3.4", "not-an-ip", "999.999.999.999"],
            },
        )
        assert response.status_code == 400
        mock_cursor.execute.assert_not_called()


class TestBatchRemove:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)
        from core.routes.api.blacklist.batch import blacklist_batch_bp

        app.register_blueprint(blacklist_batch_bp)
        app.extensions["db_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("core.routes.api.blacklist.batch.rate_limit", lambda *a, **kw: lambda f: f)
    def test_batch_remove_success(self, client, app):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.post("/blacklist/batch/remove", json={"ips": ["1.2.3.4"]})
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("core.routes.api.blacklist.batch.rate_limit", lambda *a, **kw: lambda f: f)
    def test_batch_remove_empty_list(self, client, app):
        response = client.post("/blacklist/batch/remove", json={"ips": []})
        assert response.status_code == 400


class TestBatchUpdate:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)
        from core.routes.api.blacklist.batch import blacklist_batch_bp

        app.register_blueprint(blacklist_batch_bp)
        app.extensions["db_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("core.routes.api.blacklist.batch.rate_limit", lambda *a, **kw: lambda f: f)
    def test_batch_update_success(self, client, app):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.rowcount = 1
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.post(
            "/blacklist/batch/update",
            json={
                "ips": ["1.2.3.4"],
                "reason": "updated reason",
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("core.routes.api.blacklist.batch.rate_limit", lambda *a, **kw: lambda f: f)
    def test_batch_update_no_fields(self, client, app):
        response = client.post("/blacklist/batch/update", json={"ips": ["1.2.3.4"]})
        assert response.status_code == 400

    @patch("core.routes.api.blacklist.batch.rate_limit", lambda *a, **kw: lambda f: f)
    def test_batch_update_empty_list(self, client, app):
        response = client.post("/blacklist/batch/update", json={"ips": [], "reason": "x"})
        assert response.status_code == 400
