"""Unit tests for HealthServer submit_secudium_otp endpoint."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest


def _make_health_server():
    """Create HealthServer with mock dependencies."""
    from collector.health_server import HealthServer

    mock_collector = MagicMock()
    mock_scheduler = MagicMock()

    collectors = {"SECUDIUM": mock_collector}

    server = HealthServer(
        collectors_ref=collectors,
        scheduler_ref=mock_scheduler,
        port=0,
    )
    return server, mock_collector, mock_scheduler


@pytest.mark.unit
class TestSubmitSecudiumOtp:
    """Tests for POST /api/test-auth/secudium/otp."""

    def test_otp_success_without_trigger_collect(self):
        """Auth succeeds, no collection triggered."""
        server, collector, _ = _make_health_server()
        collector.authenticate_step2.return_value = "success"
        server._secudium_pending_auth = {
            "collector": collector,
            "timestamp": datetime.now(),
        }

        with server.app.test_client() as client:
            resp = client.post(
                "/api/test-auth/secudium/otp",
                json={"otp_code": "123456"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        collector.authenticate_step2.assert_called_once_with("123456")
        collector.collect_data.assert_not_called()

    def test_otp_success_with_trigger_collect(self):
        """Auth succeeds + trigger_collect=true → runs collection."""
        server, collector, _ = _make_health_server()
        collector.authenticate_step2.return_value = "success"
        collector.collect_data.return_value = {"total_ips": 42}
        server._secudium_pending_auth = {
            "collector": collector,
            "timestamp": datetime.now(),
        }

        with server.app.test_client() as client:
            resp = client.post(
                "/api/test-auth/secudium/otp",
                json={"otp_code": "654321", "trigger_collect": True},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["collection"] is True
        assert data["collected_count"] == 42
        collector.collect_data.assert_called_once()

    def test_otp_trigger_collect_collection_fails(self):
        """Auth succeeds but collect_data() raises → collection=false with error."""
        server, collector, _ = _make_health_server()
        collector.authenticate_step2.return_value = "success"
        collector.collect_data.side_effect = RuntimeError("Connection refused")
        server._secudium_pending_auth = {
            "collector": collector,
            "timestamp": datetime.now(),
        }

        with server.app.test_client() as client:
            resp = client.post(
                "/api/test-auth/secudium/otp",
                json={"otp_code": "111111", "trigger_collect": True},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["collection"] is False
        assert "Connection refused" in data["error"]

    def test_otp_invalid_format_not_six_digits(self):
        """OTP that isn't 6 digits returns error."""
        server, collector, _ = _make_health_server()
        server._secudium_pending_auth = {
            "collector": collector,
            "timestamp": datetime.now(),
        }

        with server.app.test_client() as client:
            resp = client.post(
                "/api/test-auth/secudium/otp",
                json={"otp_code": "12345"},
            )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        collector.authenticate_step2.assert_not_called()

    def test_otp_empty_code(self):
        """Empty OTP code returns error."""
        server, collector, _ = _make_health_server()
        server._secudium_pending_auth = {
            "collector": collector,
            "timestamp": datetime.now(),
        }

        with server.app.test_client() as client:
            resp = client.post(
                "/api/test-auth/secudium/otp",
                json={"otp_code": ""},
            )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False

    def test_otp_no_pending_auth(self):
        """No pending auth session returns error."""
        server, _, _ = _make_health_server()
        # Do NOT set _secudium_pending_auth

        with server.app.test_client() as client:
            resp = client.post(
                "/api/test-auth/secudium/otp",
                json={"otp_code": "123456"},
            )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False

    def test_otp_expired_pending_auth(self):
        """Pending auth older than 5 minutes returns timeout error."""
        server, collector, _ = _make_health_server()
        server._secudium_pending_auth = {
            "collector": collector,
            "timestamp": datetime.now() - timedelta(minutes=6),
        }

        with server.app.test_client() as client:
            resp = client.post(
                "/api/test-auth/secudium/otp",
                json={"otp_code": "123456"},
            )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        collector.authenticate_step2.assert_not_called()

    def test_otp_auth_step2_failed(self):
        """authenticate_step2 returns 'failed' → error response."""
        server, collector, _ = _make_health_server()
        collector.authenticate_step2.return_value = "failed"
        server._secudium_pending_auth = {
            "collector": collector,
            "timestamp": datetime.now(),
        }

        with server.app.test_client() as client:
            resp = client.post(
                "/api/test-auth/secudium/otp",
                json={"otp_code": "999999"},
            )

        assert resp.status_code == 200  # endpoint returns 200 even on auth fail
        data = resp.get_json()
        assert data["success"] is False
