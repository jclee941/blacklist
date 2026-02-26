import pytest
from unittest.mock import MagicMock, patch
from flask import Flask, g


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    from core.routes.api.ip_management.routes import ip_management_api_bp
    from core.errors.handlers import register_error_handlers

    app.register_blueprint(ip_management_api_bp, url_prefix="/api/ip-management")
    register_error_handlers(app)

    app.extensions["db_service"] = MagicMock()

    @app.before_request
    def set_request_id():
        g.request_id = "test-request-id"

    return app


@pytest.fixture
def app():
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()


def _mock_repo(target_method, return_value):
    return patch(
        f"core.routes.api.ip_management.routes.IPManagementRepository.{target_method}",
        return_value=return_value,
    )


class TestUnifiedList:
    def test_unified_list_success(self, client, app):
        items = [{"id": 1, "ip_address": "1.2.3.4", "list_type": "blacklist"}]
        with _mock_repo("get_unified_list", (items, 1)):
            response = client.get("/api/ip-management/unified")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["pagination"]["total"] == 1

    def test_unified_list_with_filters(self, client, app):
        with _mock_repo("get_unified_list", ([], 0)):
            response = client.get("/api/ip-management/unified?type=whitelist&ip=1.2&is_active=true&source=MANUAL")
        assert response.status_code == 200

    def test_unified_list_invalid_type(self, client, app):
        response = client.get("/api/ip-management/unified?type=invalid")
        assert response.status_code == 400

    def test_unified_list_invalid_page(self, client, app):
        response = client.get("/api/ip-management/unified?page=0")
        assert response.status_code == 400

    def test_unified_list_invalid_limit(self, client, app):
        response = client.get("/api/ip-management/unified?limit=0")
        assert response.status_code == 400

    def test_unified_list_limit_over_1000(self, client, app):
        response = client.get("/api/ip-management/unified?limit=1001")
        assert response.status_code == 400

    def test_unified_list_db_error(self, client, app):
        with patch(
            "core.routes.api.ip_management.routes.IPManagementRepository.get_unified_list",
            side_effect=Exception("DB error"),
        ):
            response = client.get("/api/ip-management/unified")
        assert response.status_code == 500

    def test_list_alias(self, client, app):
        with _mock_repo("get_unified_list", ([], 0)):
            response = client.get("/api/ip-management/list")
        assert response.status_code == 200


class TestStatistics:
    def test_statistics_success(self, client, app):
        stats = [{"list_type": "blacklist", "source": "REGTECH", "count": 100}]
        with _mock_repo("get_statistics", stats):
            response = client.get("/api/ip-management/statistics")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["statistics"][0]["count"] == 100

    def test_statistics_db_error(self, client, app):
        with patch(
            "core.routes.api.ip_management.routes.IPManagementRepository.get_statistics",
            side_effect=Exception("DB error"),
        ):
            response = client.get("/api/ip-management/statistics")
        assert response.status_code == 500


class TestWhitelist:
    def test_get_whitelist_success(self, client, app):
        items = [{"id": 1, "ip_address": "10.0.0.1", "reason": "VIP"}]
        with _mock_repo("get_whitelist", (items, 1)):
            response = client.get("/api/ip-management/whitelist")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["data"]["items"]) == 1

    def test_get_whitelist_db_error(self, client, app):
        with patch(
            "core.routes.api.ip_management.routes.IPManagementRepository.get_whitelist",
            side_effect=Exception("DB error"),
        ):
            response = client.get("/api/ip-management/whitelist")
        assert response.status_code == 500

    def test_create_whitelist_success(self, client, app):
        created = {"id": 1, "ip_address": "10.0.0.1", "reason": "VIP", "source": "MANUAL"}
        with _mock_repo("create_whitelist", created):
            response = client.post(
                "/api/ip-management/whitelist",
                json={"ip_address": "10.0.0.1"},
                content_type="application/json",
            )
        assert response.status_code == 201

    def test_create_whitelist_missing_ip(self, client, app):
        response = client.post(
            "/api/ip-management/whitelist",
            json={"reason": "test"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_create_whitelist_no_body(self, client, app):
        response = client.post(
            "/api/ip-management/whitelist",
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_update_whitelist_success(self, client, app):
        updated = {"id": 1, "ip_address": "10.0.0.1", "reason": "Updated"}
        with _mock_repo("update_whitelist", updated):
            response = client.put(
                "/api/ip-management/whitelist/1",
                json={"reason": "Updated"},
                content_type="application/json",
            )
        assert response.status_code == 200

    def test_update_whitelist_not_found(self, client, app):
        with _mock_repo("update_whitelist", None):
            response = client.put(
                "/api/ip-management/whitelist/999",
                json={"reason": "test"},
                content_type="application/json",
            )
        assert response.status_code == 404

    def test_update_whitelist_empty_body(self, client, app):
        response = client.put(
            "/api/ip-management/whitelist/1",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_delete_whitelist_success(self, client, app):
        with _mock_repo("delete_whitelist", "10.0.0.1"):
            response = client.delete("/api/ip-management/whitelist/1")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["deleted_ip"] == "10.0.0.1"

    def test_delete_whitelist_not_found(self, client, app):
        with _mock_repo("delete_whitelist", None):
            response = client.delete("/api/ip-management/whitelist/999")
        assert response.status_code == 404


class TestBlacklist:
    def test_get_blacklist_success(self, client, app):
        items = [{"id": 1, "ip_address": "1.2.3.4", "reason": "malware"}]
        with _mock_repo("get_blacklist", (items, 1)):
            response = client.get("/api/ip-management/blacklist")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["data"]["items"]) == 1

    def test_get_blacklist_db_error(self, client, app):
        with patch(
            "core.routes.api.ip_management.routes.IPManagementRepository.get_blacklist",
            side_effect=Exception("DB error"),
        ):
            response = client.get("/api/ip-management/blacklist")
        assert response.status_code == 500

    def test_create_blacklist_success(self, client, app):
        created = {"id": 1, "ip_address": "1.2.3.4", "reason": "malware"}
        with _mock_repo("create_blacklist", created):
            response = client.post(
                "/api/ip-management/blacklist",
                json={"ip_address": "1.2.3.4"},
                content_type="application/json",
            )
        assert response.status_code == 201

    def test_create_blacklist_missing_ip(self, client, app):
        response = client.post(
            "/api/ip-management/blacklist",
            json={"reason": "test"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_update_blacklist_success(self, client, app):
        updated = {"id": 1, "ip_address": "1.2.3.4", "reason": "updated"}
        with _mock_repo("update_blacklist", updated):
            response = client.put(
                "/api/ip-management/blacklist/1",
                json={"reason": "updated"},
                content_type="application/json",
            )
        assert response.status_code == 200

    def test_update_blacklist_not_found(self, client, app):
        with _mock_repo("update_blacklist", None):
            response = client.put(
                "/api/ip-management/blacklist/999",
                json={"reason": "test"},
                content_type="application/json",
            )
        assert response.status_code == 404

    def test_update_blacklist_empty_body(self, client, app):
        response = client.put(
            "/api/ip-management/blacklist/1",
            json={},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_delete_blacklist_success(self, client, app):
        with _mock_repo("delete_blacklist", "1.2.3.4"):
            response = client.delete("/api/ip-management/blacklist/1")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["deleted_ip"] == "1.2.3.4"

    def test_delete_blacklist_not_found(self, client, app):
        with _mock_repo("delete_blacklist", None):
            response = client.delete("/api/ip-management/blacklist/999")
        assert response.status_code == 404
