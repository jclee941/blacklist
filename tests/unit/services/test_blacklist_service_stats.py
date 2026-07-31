from unittest.mock import MagicMock, Mock, patch

from .blacklist_service_extended_cases import make_service


class TestBlacklistServiceStats:
    def test_get_system_stats_success(self):
        svc, _, _ = make_service()
        svc.repo.count_blacklist_ips = Mock(return_value=100)
        svc.repo.count_active_blacklist_ips = Mock(return_value=50)
        svc.repo.get_source_counts = Mock(return_value={"REGTECH": 30})
        result = svc.get_system_stats()
        assert result["success"] is True
        assert result["total_ips"] == 100
        assert result["active_ips"] == 50

    def test_get_system_stats_exception(self):
        svc, _, _ = make_service()
        svc.repo.count_blacklist_ips = Mock(side_effect=Exception("fail"))
        result = svc.get_system_stats()
        assert result["success"] is False
        assert result["total_ips"] == 0

    def test_sync_with_collector_success(self):
        svc, _, _ = make_service()
        svc.repo.count_blacklist_ips = Mock(return_value=50)
        svc.repo.count_active_blacklist_ips = Mock(return_value=30)
        svc.repo.get_source_counts = Mock(return_value={})

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_resp
        mock_requests.RequestException = Exception
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = svc.sync_with_collector()
        assert result["success"] is True

    def test_sync_with_collector_unreachable(self):
        svc, _, _ = make_service()
        svc.repo.count_blacklist_ips = Mock(return_value=50)
        svc.repo.count_active_blacklist_ips = Mock(return_value=30)
        svc.repo.get_source_counts = Mock(return_value={})

        import requests as real_requests

        mock_requests = MagicMock()
        mock_requests.RequestException = real_requests.RequestException
        mock_requests.get.side_effect = real_requests.ConnectionError("refused")
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = svc.sync_with_collector()
        assert result["success"] is True
        assert "unreachable" in result.get("collector_status", "").lower() or "연결" in result.get("message", "")

    def test_force_schema_fix(self):
        svc, _, _ = make_service()
        svc.repo.add_column_if_not_exists = Mock(return_value=True)
        result = svc.force_schema_fix()
        assert result["success"] is True
        assert svc.repo.add_column_if_not_exists.call_count == 4
