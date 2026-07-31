from datetime import datetime
from unittest.mock import Mock

from .blacklist_service_extended_cases import make_service, run_async


class TestBlacklistServiceExports:
    def test_get_active_blacklist_text(self):
        svc, _, _ = make_service()
        svc.repo.get_active_blacklist_ips = Mock(return_value=["1.1.1.1", "2.2.2.2"])
        result = run_async(svc.get_active_blacklist("text"))
        assert result["success"] is True
        assert result["data"] == ["1.1.1.1", "2.2.2.2"]

    def test_get_active_blacklist_enhanced(self):
        svc, _, _ = make_service()
        enhanced_data = [
            {
                "ip_address": "1.1.1.1",
                "reason": "malicious",
                "source": "REGTECH",
                "is_active": True,
                "last_seen": datetime(2024, 1, 1),
                "detection_count": 5,
            }
        ]
        svc.repo.get_active_blacklist_enhanced = Mock(return_value=enhanced_data)
        result = run_async(svc.get_active_blacklist("enhanced"))
        assert result["success"] is True

    def test_get_active_blacklist_fortigate(self):
        svc, _, _ = make_service()
        svc.repo.get_active_blacklist_ips = Mock(return_value=["1.1.1.1"])
        result = run_async(svc.get_active_blacklist("fortigate"))
        assert result["success"] is True
        assert "entries" in result["data"]

    def test_get_active_blacklist_exception(self):
        svc, _, _ = make_service()
        svc.repo.get_active_blacklist_ips = Mock(side_effect=Exception("db error"))
        result = run_async(svc.get_active_blacklist("text"))
        assert result["success"] is False
        assert "error" in result
