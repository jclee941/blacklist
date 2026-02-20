from unittest.mock import MagicMock, patch
from flask import Flask
from datetime import datetime

from core.routes.web.settings import settings_bp


def make_app(mock_svc=None):
    app = Flask(__name__, template_folder="/app/templates")
    app.config["TESTING"] = True
    if mock_svc is not None:
        app.extensions["settings_service"] = mock_svc
    app.register_blueprint(settings_bp)
    return app


class TestGetAllSettings:
    def test_success(self):
        mock_svc = MagicMock()
        mock_svc.get_all_settings.return_value = [{"key": "k1", "value": "v1"}]
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.get("/settings/api/settings")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["count"] == 1

    def test_with_category_filter(self):
        mock_svc = MagicMock()
        mock_svc.get_all_settings.return_value = []
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.get("/settings/api/settings?category=security")

        assert resp.status_code == 200
        mock_svc.get_all_settings.assert_called_once_with(category="security", include_encrypted=False)

    def test_exception(self):
        mock_svc = MagicMock()
        mock_svc.get_all_settings.side_effect = Exception("crash")
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.get("/settings/api/settings")

        assert resp.status_code == 500


class TestGetSettingsGrouped:
    def test_success(self):
        mock_svc = MagicMock()
        mock_svc.get_settings_by_category.return_value = {"general": [{"key": "k1"}], "security": []}
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.get("/settings/api/settings/grouped")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "general" in data["categories"]

    def test_exception(self):
        mock_svc = MagicMock()
        mock_svc.get_settings_by_category.side_effect = Exception("crash")
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.get("/settings/api/settings/grouped")

        assert resp.status_code == 500


class TestGetSetting:
    def test_found(self):
        mock_svc = MagicMock()
        mock_svc.get_setting.return_value = "my_value"
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.get("/settings/api/settings/my_key")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["value"] == "my_value"
        assert data["key"] == "my_key"

    def test_not_found(self):
        mock_svc = MagicMock()
        mock_svc.get_setting.return_value = None
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.get("/settings/api/settings/missing")

        assert resp.status_code == 404

    def test_exception(self):
        mock_svc = MagicMock()
        mock_svc.get_setting.side_effect = Exception("crash")
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.get("/settings/api/settings/key1")

        assert resp.status_code == 500


class TestUpdateSetting:
    def test_success(self):
        mock_svc = MagicMock()
        mock_svc.set_setting.return_value = True
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.put("/settings/api/settings/my_key", json={"value": "new_val"})

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_missing_value(self):
        mock_svc = MagicMock()
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.put("/settings/api/settings/my_key", json={})

        assert resp.status_code == 400

    def test_set_fails(self):
        mock_svc = MagicMock()
        mock_svc.set_setting.return_value = False
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.put("/settings/api/settings/my_key", json={"value": "x"})

        assert resp.status_code == 500

    def test_with_encrypt_flag(self):
        mock_svc = MagicMock()
        mock_svc.set_setting.return_value = True
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.put("/settings/api/settings/secret_key", json={"value": "secret", "encrypt": True})

        assert resp.status_code == 200
        mock_svc.set_setting.assert_called_once_with("secret_key", "secret", encrypt=True)


class TestCreateSetting:
    def test_success(self):
        mock_svc = MagicMock()
        mock_svc.create_setting.return_value = True
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.post(
                "/settings/api/settings",
                json={"key": "new_key", "value": "val", "type": "string"},
            )

        assert resp.status_code == 201
        assert resp.get_json()["success"] is True

    def test_missing_required_field(self):
        mock_svc = MagicMock()
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.post("/settings/api/settings", json={"key": "k"})

        assert resp.status_code == 400

    def test_create_fails(self):
        mock_svc = MagicMock()
        mock_svc.create_setting.return_value = False
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.post(
                "/settings/api/settings",
                json={"key": "k", "value": "v", "type": "string"},
            )

        assert resp.status_code == 500


class TestDeleteSetting:
    def test_success(self):
        mock_svc = MagicMock()
        mock_svc.delete_setting.return_value = True
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.delete("/settings/api/settings/old_key")

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_not_found(self):
        mock_svc = MagicMock()
        mock_svc.delete_setting.return_value = False
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.delete("/settings/api/settings/missing")

        assert resp.status_code == 404

    def test_exception(self):
        mock_svc = MagicMock()
        mock_svc.delete_setting.side_effect = Exception("crash")
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.delete("/settings/api/settings/key1")

        assert resp.status_code == 500


class TestBatchUpdateSettings:
    def test_success(self):
        mock_svc = MagicMock()
        mock_svc.set_setting.return_value = True
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.put(
                "/settings/api/settings/batch",
                json={"settings": [{"key": "k1", "value": "v1"}, {"key": "k2", "value": "v2"}]},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert mock_svc.set_setting.call_count == 2

    def test_missing_settings_array(self):
        mock_svc = MagicMock()
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.put("/settings/api/settings/batch", json={})

        assert resp.status_code == 400

    def test_exception(self):
        mock_svc = MagicMock()
        mock_svc.set_setting.side_effect = Exception("crash")
        app = make_app(mock_svc)

        with app.test_client() as c:
            resp = c.put(
                "/settings/api/settings/batch",
                json={"settings": [{"key": "k1", "value": "v1"}]},
            )

        assert resp.status_code == 500


class TestSettingsPage:
    @patch("core.routes.web.settings.render_template")
    def test_success(self, mock_render):
        mock_render.return_value = "<html>settings</html>"
        app = make_app()

        with app.test_client() as c:
            resp = c.get("/settings/")

        assert resp.status_code == 200
        mock_render.assert_called_once_with("settings.html")

    @patch("core.routes.web.settings.render_template")
    def test_exception(self, mock_render):
        mock_render.side_effect = Exception("template not found")
        app = make_app()

        with app.test_client() as c:
            resp = c.get("/settings/")

        assert resp.status_code == 500


class TestGetAllCredentials:
    def test_success_with_rows(self):
        app = make_app()
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ("REGTECH", "admin", True, datetime(2026, 1, 1), datetime(2026, 1, 2), {"key": "val"}),
        ]
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/settings/api/credentials")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["count"] == 1
        cred = data["credentials"][0]
        assert cred["service_name"] == "REGTECH"
        assert cred["username"] == "admin"
        assert cred["password"] == "********"
        assert cred["is_active"] is True
        assert cred["created_at"] == "2026-01-01T00:00:00"
        assert cred["updated_at"] == "2026-01-02T00:00:00"
        assert cred["config"] == {"key": "val"}

    def test_empty_result(self):
        app = make_app()
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/settings/api/credentials")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 0
        assert data["credentials"] == []

    def test_null_dates_and_config(self):
        app = make_app()
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ("SVC1", "user1", False, None, None, None),
        ]
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/settings/api/credentials")

        assert resp.status_code == 200
        cred = resp.get_json()["credentials"][0]
        assert cred["created_at"] is None
        assert cred["updated_at"] is None
        assert cred["config"] == {}

    def test_exception(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_connection.side_effect = Exception("db down")
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/settings/api/credentials")

        assert resp.status_code == 500
        assert resp.get_json()["success"] is False


class TestUpdateCredentials:
    def _make_db_mock(self):
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        return mock_db, mock_conn, mock_cursor

    def test_success(self):
        mock_db, mock_conn, mock_cursor = self._make_db_mock()
        mock_cursor.fetchone.return_value = ("REGTECH",)
        app = make_app()
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.put(
                "/settings/api/credentials/regtech",
                json={"username": "new_user", "password": "new_pass"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["service_name"] == "regtech"
        mock_conn.commit.assert_called_once()

    def test_not_found(self):
        mock_db, mock_conn, mock_cursor = self._make_db_mock()
        mock_cursor.fetchone.return_value = None
        app = make_app()
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.put("/settings/api/credentials/unknown", json={"username": "u"})

        assert resp.status_code == 404

    def test_empty_body(self):
        app = make_app()
        mock_db = MagicMock()
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.put("/settings/api/credentials/regtech", json={})

        assert resp.status_code == 400

    def test_no_recognized_fields(self):
        app = make_app()
        mock_db = MagicMock()
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.put("/settings/api/credentials/regtech", json={"unknown_field": "value"})

        assert resp.status_code == 400
        assert "No fields to update" in resp.get_json()["error"]

    def test_exception_rollback(self):
        mock_db, mock_conn, mock_cursor = self._make_db_mock()
        mock_cursor.execute.side_effect = Exception("sql error")
        app = make_app()
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.put("/settings/api/credentials/regtech", json={"username": "u"})

        assert resp.status_code == 500
        mock_conn.rollback.assert_called_once()

    def test_update_with_config_and_is_active(self):
        mock_db, mock_conn, mock_cursor = self._make_db_mock()
        mock_cursor.fetchone.return_value = ("SVC",)
        app = make_app()
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.put(
                "/settings/api/credentials/svc",
                json={"config": {"url": "https://x"}, "is_active": False},
            )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


class TestCreateCredentials:
    def _make_db_mock(self):
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        return mock_db, mock_conn, mock_cursor

    def test_success(self):
        mock_db, mock_conn, mock_cursor = self._make_db_mock()
        mock_cursor.fetchone.return_value = ("NEW_SVC",)
        app = make_app()
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.post(
                "/settings/api/credentials",
                json={"service_name": "NEW_SVC", "username": "user", "password": "pass"},
            )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert data["service_name"] == "NEW_SVC"
        mock_conn.commit.assert_called_once()

    def test_missing_required_field(self):
        app = make_app()
        mock_db = MagicMock()
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.post(
                "/settings/api/credentials",
                json={"service_name": "x", "username": "u"},
            )

        assert resp.status_code == 400
        assert "password" in resp.get_json()["error"]

    def test_fetchone_returns_none(self):
        mock_db, mock_conn, mock_cursor = self._make_db_mock()
        mock_cursor.fetchone.return_value = None
        app = make_app()
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.post(
                "/settings/api/credentials",
                json={"service_name": "SVC", "username": "u", "password": "p"},
            )

        assert resp.status_code == 500
        assert resp.get_json()["success"] is False

    def test_exception_rollback(self):
        mock_db, mock_conn, mock_cursor = self._make_db_mock()
        mock_cursor.execute.side_effect = Exception("insert failed")
        app = make_app()
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.post(
                "/settings/api/credentials",
                json={"service_name": "SVC", "username": "u", "password": "p"},
            )

        assert resp.status_code == 500
        mock_conn.rollback.assert_called_once()

    def test_with_config(self):
        mock_db, mock_conn, mock_cursor = self._make_db_mock()
        mock_cursor.fetchone.return_value = ("SVC",)
        app = make_app()
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.post(
                "/settings/api/credentials",
                json={
                    "service_name": "SVC",
                    "username": "u",
                    "password": "p",
                    "config": {"url": "https://example.com"},
                },
            )

        assert resp.status_code == 201


class TestSettingsHealth:
    def test_healthy(self):
        app = make_app()
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/settings/api/health")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        mock_db.return_connection.assert_called_once_with(mock_conn)

    def test_unhealthy(self):
        app = make_app()
        mock_db = MagicMock()
        mock_db.get_connection.side_effect = Exception("connection refused")
        app.extensions["db_service"] = mock_db

        with app.test_client() as c:
            resp = c.get("/settings/api/health")

        assert resp.status_code == 500
        data = resp.get_json()
        assert data["success"] is False
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
