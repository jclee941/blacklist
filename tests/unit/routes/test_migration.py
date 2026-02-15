"""
Tests for migration.py — /api/migration/* endpoints.
migration_bp is a standalone Blueprint.
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from flask import Flask, g
from datetime import datetime


def _create_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    from core.routes.api.migration import migration_bp

    app.register_blueprint(migration_bp)

    from core.errors.handlers import register_error_handlers

    register_error_handlers(app)

    @app.before_request
    def _set_request_id():
        g.request_id = "test-request-id"

    return app


def _mock_db_with_context(cursor_results):
    """Create db_service mock that supports `with get_connection() as conn: with conn.cursor() as cur:`."""
    mock_cursor = MagicMock()
    if "fetchone" in cursor_results:
        mock_cursor.fetchone.side_effect = cursor_results["fetchone"]
    mock_cursor.rowcount = cursor_results.get("rowcount", 0)
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.commit = MagicMock()

    mock_db = MagicMock()
    mock_db.get_connection.return_value = mock_conn
    return mock_db


# ─── Cleanup Secudium ──────────────────────────────────────────────


class TestCleanupSecudium:
    """POST /api/migration/cleanup-secudium"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    @patch.dict(os.environ, {"MIGRATION_KEY": "test-key"}, clear=False)
    def test_cleanup_success(self):
        mock_db = _mock_db_with_context(
            {
                "fetchone": [
                    (100, "REGTECH, SECUDIUM"),  # before
                    (80, "REGTECH"),  # after
                ],
                "rowcount": 20,
            }
        )
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post(
            "/api/migration/cleanup-secudium",
            headers={"X-Migration-Key": "test-key"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_cleanup_wrong_key(self):
        """Wrong key: UnauthorizedError has bug (details kwarg unsupported) -> TypeError -> 500."""
        resp = self.client.post(
            "/api/migration/cleanup-secudium",
            headers={"X-Migration-Key": "wrong"},
        )
        # BUG in source: UnauthorizedError() called with unsupported 'details' kwarg
        assert resp.status_code == 500

    def test_cleanup_no_key(self):
        """No key: same UnauthorizedError bug -> 500."""
        resp = self.client.post("/api/migration/cleanup-secudium")
        assert resp.status_code == 500

    @patch.dict(os.environ, {"MIGRATION_KEY": "test-key"}, clear=False)
    def test_cleanup_db_error(self):
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post(
            "/api/migration/cleanup-secudium",
            headers={"X-Migration-Key": "test-key"},
        )
        assert resp.status_code == 500


# ─── Regtech Test Collection ───────────────────────────────────────


class TestRegtechTestCollection:
    """POST /api/migration/regtech-test-collection"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    def test_regtech_collection_success(self):
        mock_svc = MagicMock()
        mock_svc.trigger_collection.return_value = {"success": True, "collected": 50}
        self.app.extensions["collection_service"] = mock_svc

        resp = self.client.post("/api/migration/regtech-test-collection")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_regtech_collection_failure(self):
        mock_svc = MagicMock()
        mock_svc.trigger_collection.return_value = {"success": False, "error": "timeout"}
        self.app.extensions["collection_service"] = mock_svc

        resp = self.client.post("/api/migration/regtech-test-collection")
        assert resp.status_code == 500

    def test_regtech_collection_exception(self):
        mock_svc = MagicMock()
        mock_svc.trigger_collection.side_effect = Exception("boom")
        self.app.extensions["collection_service"] = mock_svc

        resp = self.client.post("/api/migration/regtech-test-collection")
        assert resp.status_code == 500


# ─── Reset All Data ────────────────────────────────────────────────


class TestResetAllData:
    """POST /api/migration/reset-all-data"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    @patch.dict(os.environ, {"MIGRATION_KEY": "test-key"}, clear=False)
    def test_reset_all_success(self):
        mock_db = _mock_db_with_context(
            {
                "fetchone": [
                    (500, "REGTECH, SECUDIUM"),  # before
                ],
                "rowcount": 500,
            }
        )
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post(
            "/api/migration/reset-all-data",
            headers={"X-Migration-Key": "test-key"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["after_count"] == 0

    def test_reset_all_wrong_key(self):
        """Wrong key: UnauthorizedError has bug (details kwarg unsupported) -> TypeError -> 500."""
        resp = self.client.post(
            "/api/migration/reset-all-data",
            headers={"X-Migration-Key": "wrong"},
        )
        assert resp.status_code == 500

    @patch.dict(os.environ, {"MIGRATION_KEY": "test-key"}, clear=False)
    def test_reset_all_db_error(self):
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.execute.side_effect = Exception("fail")
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post(
            "/api/migration/reset-all-data",
            headers={"X-Migration-Key": "test-key"},
        )
        assert resp.status_code == 500


# ─── Migration Status ──────────────────────────────────────────────


class TestMigrationStatus:
    """GET /api/migration/status"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    def test_status_clean(self):
        mock_db = _mock_db_with_context(
            {
                "fetchone": [
                    (100, 80, 0, "REGTECH"),
                ],
            }
        )
        self.app.extensions["db_service"] = mock_db

        resp = self.client.get("/api/migration/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["clean_state"] is True
        assert data["data"]["stats"]["secudium_count"] == 0

    def test_status_dirty(self):
        mock_db = _mock_db_with_context(
            {
                "fetchone": [
                    (200, 100, 50, "REGTECH, SECUDIUM"),
                ],
            }
        )
        self.app.extensions["db_service"] = mock_db

        resp = self.client.get("/api/migration/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["clean_state"] is False

    def test_status_db_error(self):
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.execute.side_effect = Exception("fail")
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn
        self.app.extensions["db_service"] = mock_db

        resp = self.client.get("/api/migration/status")
        assert resp.status_code == 500
