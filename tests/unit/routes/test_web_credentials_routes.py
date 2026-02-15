from unittest.mock import MagicMock
from flask import Flask

from core.routes.web.credentials_routes import credentials_bp


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(credentials_bp)
    return app


class TestGetCredentials:
    def test_found(self):
        app = make_app()
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = ("admin", True, True, "2026-01-01")
        mock_conn.cursor.return_value = mock_cur
        mock_db.get_connection.return_value = mock_conn
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/api/collection/credentials/regtech")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == "admin"
        assert data["password"] == "********"
        assert data["enabled"] is True

    def test_not_found(self):
        app = make_app()
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cur
        mock_db.get_connection.return_value = mock_conn
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/api/collection/credentials/regtech")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == ""
        assert data["enabled"] is False

    def test_error(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_connection.side_effect = Exception("db down")
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/api/collection/credentials/regtech")

        assert resp.status_code == 500
        assert "db down" in resp.get_json()["error"]


class TestSaveCredentials:
    def test_update_existing(self):
        app = make_app()
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cur
        mock_db.get_connection.return_value = mock_conn
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.post(
                "/api/collection/credentials/regtech",
                json={"username": "user1", "password": "pass1"},
            )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True
        mock_conn.commit.assert_called_once()

    def test_insert_when_not_exists(self):
        app = make_app()
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = [None, (1,)]
        mock_conn.cursor.return_value = mock_cur
        mock_db.get_connection.return_value = mock_conn
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.put(
                "/api/collection/credentials/regtech",
                json={"username": "user1", "password": "pass1"},
            )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True
        assert mock_cur.execute.call_count == 2

    def test_error(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_connection.side_effect = Exception("db down")
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.post(
                "/api/collection/credentials/regtech",
                json={"username": "u", "password": "p"},
            )

        assert resp.status_code == 500


class TestTestCredentials:
    def test_always_succeeds(self):
        app = make_app()

        with app.test_client() as c:
            resp = c.post("/api/collection/credentials/regtech/test")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "regtech" in data["message"]
