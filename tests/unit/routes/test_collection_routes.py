import pytest
from unittest.mock import Mock, MagicMock, patch
from flask import Flask, g
from datetime import datetime

from core.errors.handlers import register_error_handlers


def make_app_with_blueprint(bp, url_prefix=None):
    """Create test app with a single collection blueprint"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_error_handlers(app)
    if url_prefix:
        app.register_blueprint(bp, url_prefix=url_prefix)
    else:
        app.register_blueprint(bp)
    app.extensions["db_service"] = Mock()
    app.extensions["settings_service"] = Mock()
    app.extensions["blacklist_service"] = Mock()
    app.extensions["collection_service"] = Mock()

    @app.before_request
    def set_request_id():
        g.request_id = "test-request-id"

    return app


# ============================================================
# Sources API Tests
# ============================================================
class TestCollectionSources:
    @pytest.fixture
    def app(self):
        from core.routes.api.collection.sources import sources_bp

        return make_app_with_blueprint(sources_bp, url_prefix="/api/collection")

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_list_sources(self, client):
        """GET /api/collection/sources returns available sources"""
        response = client.get("/api/collection/sources")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["sources"]) == 1
        assert data["summary"]["total"] == 1

    def test_get_source_found(self, client):
        """GET /api/collection/sources/REGTECH returns source details"""
        response = client.get("/api/collection/sources/REGTECH")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["source"]["id"] == "REGTECH"

    def test_get_source_case_insensitive(self, client):
        """GET /api/collection/sources/regtech returns source (uppercased)"""
        response = client.get("/api/collection/sources/regtech")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_get_source_not_found(self, client):
        """GET /api/collection/sources/UNKNOWN returns 404"""
        response = client.get("/api/collection/sources/UNKNOWN")
        assert response.status_code == 404

    def test_get_source_status_success(self, client, app):
        """GET /api/collection/sources/REGTECH/status with collection history"""
        app.extensions["db_service"].query.return_value = [
            {
                "id": 1,
                "service_name": "REGTECH",
                "collection_date": datetime(2026, 1, 1, 12, 0),
                "items_collected": 500,
                "success": True,
                "error_message": None,
            }
        ]

        response = client.get("/api/collection/sources/REGTECH/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["status"] == "success"

    def test_get_source_status_never_collected(self, client, app):
        """GET /api/collection/sources/REGTECH/status with no history"""
        app.extensions["db_service"].query.return_value = []

        response = client.get("/api/collection/sources/REGTECH/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "never_collected"

    def test_get_source_status_not_found(self, client):
        """GET /api/collection/sources/UNKNOWN/status returns 404"""
        response = client.get("/api/collection/sources/UNKNOWN/status")
        assert response.status_code == 404

    def test_get_source_status_no_db(self, client, app):
        """GET /api/collection/sources/REGTECH/status without db_service"""
        del app.extensions["db_service"]

        response = client.get("/api/collection/sources/REGTECH/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "unknown"


# ============================================================
# Config API Tests
# ============================================================
class TestCollectionConfig:
    @pytest.fixture
    def app(self):
        from core.routes.api.collection.config import collection_config_bp

        return make_app_with_blueprint(collection_config_bp, url_prefix="/api")

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_update_config_success(self, client, app):
        """POST /api/collection/config/update with valid data"""
        app.extensions["settings_service"].set_setting.return_value = True

        response = client.post(
            "/api/collection/config/update",
            json={"interval": 3600, "enabled": True},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "interval" in data["data"]["updated"]
        assert "enabled" in data["data"]["updated"]

    def test_update_config_empty_body(self, client):
        """POST /api/collection/config/update with empty body returns 400"""
        response = client.post("/api/collection/config/update", json={})
        assert response.status_code == 400

    def test_update_config_partial_failure(self, client, app):
        """POST /api/collection/config/update with partial success returns 500"""

        def mock_set_setting(key, value):
            return key == "collection_interval"

        app.extensions["settings_service"].set_setting.side_effect = mock_set_setting

        response = client.post(
            "/api/collection/config/update",
            json={"interval": 3600, "enabled": True},
        )
        assert response.status_code == 500

    def test_update_config_total_failure(self, client, app):
        """POST /api/collection/config/update with all keys failing returns 500"""
        app.extensions["settings_service"].set_setting.return_value = False

        response = client.post(
            "/api/collection/config/update",
            json={"interval": 3600},
        )
        assert response.status_code == 500


# ============================================================
# History API Tests
# ============================================================
class TestCollectionHistory:
    @pytest.fixture
    def app(self):
        from core.routes.api.collection.history import collection_history_bp

        return make_app_with_blueprint(collection_history_bp, url_prefix="/api/collection")

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_history_success(self, client, app):
        """GET /api/collection/history returns collection history"""
        app.extensions["db_service"].query.side_effect = [
            [
                {
                    "id": 1,
                    "service_name": "REGTECH",
                    "collection_date": datetime(2026, 1, 1, 12, 0),
                    "items_collected": 500,
                    "success": True,
                    "duration_seconds": 10.5,
                    "error_message": None,
                    "metadata": {"new_count": 400, "updated_count": 100},
                }
            ],
            [{"total": 1}],
        ]

        response = client.get("/api/collection/history")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]["history"]) == 1
        assert data["data"]["history"][0]["items_collected"] == 500

    def test_history_with_source_filter(self, client, app):
        """GET /api/collection/history?source=REGTECH filters by source"""
        app.extensions["db_service"].query.return_value = []

        response = client.get("/api/collection/history?source=REGTECH")
        assert response.status_code == 200

    def test_history_applies_page_offset_and_returns_total(self, client, app):
        rows = [
            {
                "id": index,
                "service_name": "REGTECH",
                "collection_date": datetime(2026, 1, 1, 12, 0),
                "items_collected": 1,
                "success": True,
                "duration_seconds": 1.0,
                "error_message": None,
                "metadata": {},
            }
            for index in range(20)
        ]
        app.extensions["db_service"].query.side_effect = [rows, [{"total": 45}]]

        response = client.get("/api/collection/history?source=REGTECH&page=2&per_page=20")

        assert response.status_code == 200
        assert response.get_json()["data"]["total"] == 45
        query, params = app.extensions["db_service"].query.call_args_list[0].args
        assert "OFFSET %s" in query
        assert params == ("REGTECH", 20, 20)

    def test_history_invalid_limit(self, client):
        """GET /api/collection/history?limit=500 returns 400"""
        response = client.get("/api/collection/history?limit=500")
        assert response.status_code == 400

    def test_history_limit_zero(self, client):
        """GET /api/collection/history?limit=0 returns 400"""
        response = client.get("/api/collection/history?limit=0")
        assert response.status_code == 400

    def test_history_db_error(self, client, app):
        """GET /api/collection/history with DB error returns 500"""
        app.extensions["db_service"].query.side_effect = Exception("DB down")

        response = client.get("/api/collection/history")
        assert response.status_code == 500

    def test_statistics_success(self, client, app):
        """GET /api/collection/statistics returns stats"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        # Mock fetchone calls for today/week/month/ip_counts
        mock_cursor.fetchone.side_effect = [
            {"today_collected": 100},
            {"week_collected": 500},
            {"month_collected": 2000},
            {"total_ips": 5000, "active_ips": 3000},
        ]
        # Mock fetchall for source stats
        mock_cursor.fetchall.return_value = []
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.get("/api/collection/statistics")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["today_collected"] == 100
        assert data["data"]["current_total_ips"] == 5000

    def test_statistics_db_error(self, client, app):
        """GET /api/collection/statistics with DB error returns 500"""
        app.extensions["db_service"].get_connection.side_effect = Exception("DB down")

        response = client.get("/api/collection/statistics")
        assert response.status_code == 500


# ============================================================
# Sync API Tests
# ============================================================
class TestCollectionSync:
    @pytest.fixture
    def app(self):
        from core.routes.api.collection.sync import collection_sync_bp

        return make_app_with_blueprint(collection_sync_bp, url_prefix="/api")

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_sync_collector_success(self, client, app):
        """GET /api/sync/collector returns sync result"""
        app.extensions["blacklist_service"].sync_with_collector.return_value = {"synced": True, "items": 100}

        response = client.get("/api/sync/collector")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["synced"] is True

    def test_sync_collector_error(self, client, app):
        """GET /api/sync/collector with service error returns 500"""
        app.extensions["blacklist_service"].sync_with_collector.side_effect = Exception("Sync failed")

        response = client.get("/api/sync/collector")
        assert response.status_code == 500

    def test_force_data_refresh_success(self, client, app):
        """POST /api/data/refresh triggers data refresh"""
        app.extensions["collection_service"].force_refresh.return_value = {"refreshed": True}

        response = client.post("/api/data/refresh")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_force_data_refresh_error(self, client, app):
        """POST /api/data/refresh with error returns 500"""
        app.extensions["collection_service"].force_refresh.side_effect = Exception("Refresh failed")

        response = client.post("/api/data/refresh")
        assert response.status_code == 500


# ============================================================
# Status API Tests
# ============================================================
class TestCollectionStatus:
    @pytest.fixture
    def app(self):
        from core.routes.api.collection.status import collection_status_bp

        return make_app_with_blueprint(collection_status_bp, url_prefix="/api/collection")

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("core.routes.api.collection.status.call_collector_api")
    def test_status_healthy(self, mock_call, client):
        """GET /api/collection/status returns healthy status"""
        mock_call.return_value = {
            "status": "healthy",
            "collectors": {
                "REGTECH": {"enabled": True, "last_run": None, "interval_seconds": 86400},
            },
        }

        response = client.get("/api/collection/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "collectors" in data["data"]
        mock_call.assert_called_once_with("/status")

    @patch("core.routes.api.collection.status.call_collector_api")
    def test_status_collector_unavailable(self, mock_call, client):
        """GET /api/collection/status when collector is down returns 500"""
        mock_call.return_value = {
            "success": False,
            "error": "Cannot connect to collector",
        }

        response = client.get("/api/collection/status")
        assert response.status_code == 500

    @patch("core.routes.api.collection.status.call_collector_api")
    def test_status_unexpected_format(self, mock_call, client):
        """GET /api/collection/status with unexpected response format"""
        mock_call.return_value = {"status": "unknown"}

        response = client.get("/api/collection/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["is_running"] is False

    @patch("core.routes.api.collection.status.call_collector_api")
    def test_health_all_healthy(self, mock_call, client, app):
        """GET /api/collection/health with all services healthy"""
        mock_call.return_value = {"status": "healthy"}
        app.extensions["db_service"].health_check.return_value = True

        response = client.get("/api/collection/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"

    @patch("core.routes.api.collection.status.call_collector_api")
    def test_health_db_unhealthy(self, mock_call, client, app):
        """GET /api/collection/health with DB unhealthy"""
        mock_call.return_value = {"status": "healthy"}
        app.extensions["db_service"].health_check.return_value = False

        response = client.get("/api/collection/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["status"] == "unhealthy"
        assert "Network error" not in response.get_data(as_text=True)

    @patch("core.routes.api.collection.status.call_collector_api")
    def test_health_error_graceful(self, mock_call, client, app):
        """GET /api/collection/health with exception returns unhealthy 200"""
        mock_call.side_effect = Exception("Network error")

        response = client.get("/api/collection/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["status"] == "unhealthy"
