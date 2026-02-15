"""Tests for collector/scheduler_api.py — scheduler management REST API."""

import pytest
from unittest.mock import MagicMock
from collector.scheduler_api import create_scheduler_api


def make_scheduler_mock(**overrides):
    scheduler = MagicMock()
    scheduler.collectors = {"REGTECH": "collect_regtech", "SECUDIUM": "collect_secudium"}
    scheduler.running = True
    scheduler.collection_stats = {
        "total_runs": 10,
        "successful_runs": 8,
        "failed_runs": 2,
        "last_run": "2025-01-01T00:00:00",
        "last_success": "2025-01-01T00:00:00",
    }
    scheduler.get_status.return_value = {"running": True, "uptime": "1h"}
    scheduler.force_collection.return_value = {"success": True, "collected": 42}
    for k, v in overrides.items():
        setattr(scheduler, k, v)
    return scheduler


class TestGetStatus:
    def test_status_success(self):
        scheduler = make_scheduler_mock()
        app = create_scheduler_api(scheduler)
        client = app.test_client()

        resp = client.get("/api/scheduler/status")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["running"] is True

    def test_status_exception(self):
        scheduler = make_scheduler_mock()
        scheduler.get_status.side_effect = RuntimeError("broken")
        app = create_scheduler_api(scheduler)
        client = app.test_client()

        resp = client.get("/api/scheduler/status")

        assert resp.status_code == 500
        assert resp.get_json()["success"] is False


class TestForceCollection:
    def test_force_known_source(self):
        scheduler = make_scheduler_mock()
        app = create_scheduler_api(scheduler)
        client = app.test_client()

        resp = client.post("/api/scheduler/force-collection/regtech")

        assert resp.status_code == 200
        scheduler.force_collection.assert_called_once_with("REGTECH")

    def test_force_unknown_source(self):
        scheduler = make_scheduler_mock()
        app = create_scheduler_api(scheduler)
        client = app.test_client()

        resp = client.post("/api/scheduler/force-collection/unknown")

        assert resp.status_code == 400
        assert "Unknown source" in resp.get_json()["error"]

    def test_force_collection_exception(self):
        scheduler = make_scheduler_mock()
        scheduler.force_collection.side_effect = RuntimeError("timeout")
        app = create_scheduler_api(scheduler)
        client = app.test_client()

        resp = client.post("/api/scheduler/force-collection/regtech")

        assert resp.status_code == 500


class TestRestartScheduler:
    def test_restart_success(self):
        scheduler = make_scheduler_mock()
        app = create_scheduler_api(scheduler)
        client = app.test_client()

        resp = client.post("/api/scheduler/restart")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        scheduler.stop.assert_called_once()
        scheduler.start.assert_called_once()

    def test_restart_exception(self):
        scheduler = make_scheduler_mock()
        scheduler.stop.side_effect = RuntimeError("stuck")
        app = create_scheduler_api(scheduler)
        client = app.test_client()

        resp = client.post("/api/scheduler/restart")

        assert resp.status_code == 500


class TestListCollectors:
    def test_list_success(self):
        scheduler = make_scheduler_mock()
        app = create_scheduler_api(scheduler)
        client = app.test_client()

        resp = client.get("/api/scheduler/collectors")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["total"] == 2
        assert "REGTECH" in data["collectors"]
        assert "SECUDIUM" in data["collectors"]
        assert data["scheduler_running"] is True

    def test_list_exception(self):
        scheduler = make_scheduler_mock()
        scheduler.collection_stats = None
        type(scheduler).collection_stats = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        app = create_scheduler_api(scheduler)
        client = app.test_client()

        resp = client.get("/api/scheduler/collectors")

        assert resp.status_code == 500
