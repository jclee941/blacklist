from unittest.mock import MagicMock
from flask import Flask

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
