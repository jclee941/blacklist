"""Extended tests for blacklist_service.py - covers uncovered methods."""

import asyncio
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


def run_async(coro):
    """Run async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestBlacklistServiceExtended:
    """Additional tests for BlacklistService methods not covered in base tests."""

    def _make_service(self):
        mock_db = Mock()
        mock_redis = MagicMock()
        with patch("core.services.blacklist_service.redis.Redis", return_value=mock_redis):
            from core.services.blacklist_service import BlacklistService

            svc = BlacklistService(db_service=mock_db)
        svc.repo = Mock()
        svc.redis_client = mock_redis
        svc.db_service = mock_db
        return svc, mock_db, mock_redis

    # ---- get_active_blacklist ----

    def test_get_active_blacklist_text(self):
        svc, _, _ = self._make_service()
        svc.repo.get_active_blacklist_ips = Mock(return_value=["1.1.1.1", "2.2.2.2"])
        result = run_async(svc.get_active_blacklist("text"))
        assert result["success"] is True
        assert result["data"] == ["1.1.1.1", "2.2.2.2"]

    def test_get_active_blacklist_enhanced(self):

        svc, _, _ = self._make_service()
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
        svc, _, _ = self._make_service()
        svc.repo.get_active_blacklist_ips = Mock(return_value=["1.1.1.1"])
        result = run_async(svc.get_active_blacklist("fortigate"))
        assert result["success"] is True
        assert "entries" in result["data"]

    def test_get_active_blacklist_exception(self):
        svc, _, _ = self._make_service()
        svc.repo.get_active_blacklist_ips = Mock(side_effect=Exception("db error"))
        result = run_async(svc.get_active_blacklist("text"))
        assert result["success"] is False
        assert "error" in result

    # ---- get_system_stats ----

    def test_get_system_stats_success(self):
        svc, _, _ = self._make_service()
        svc.repo.count_blacklist_ips = Mock(return_value=100)
        svc.repo.count_active_blacklist_ips = Mock(return_value=50)
        svc.repo.get_source_counts = Mock(return_value={"REGTECH": 30, "SECUDIUM": 20})
        result = svc.get_system_stats()
        assert result["success"] is True
        assert result["total_ips"] == 100
        assert result["active_ips"] == 50

    def test_get_system_stats_exception(self):
        svc, _, _ = self._make_service()
        svc.repo.count_blacklist_ips = Mock(side_effect=Exception("fail"))
        result = svc.get_system_stats()
        assert result["success"] is False
        assert result["total_ips"] == 0

    # ---- enable/disable collection ----

    def test_enable_collection(self):
        svc, _, _ = self._make_service()
        result = run_async(svc.enable_collection())
        assert result["success"] is True

    def test_disable_collection(self):
        svc, _, _ = self._make_service()
        result = run_async(svc.disable_collection())
        assert result["success"] is True

    # ---- collect_all_data / _collect_regtech_data ----

    def test_collect_regtech_data_success(self):
        svc, _, _ = self._make_service()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"collected": 10}

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_resp
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = run_async(svc._collect_regtech_data(force=True))
        assert result["success"] is True

    def test_collect_regtech_data_non_200(self):
        svc, _, _ = self._make_service()
        mock_resp = Mock()
        mock_resp.status_code = 500

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_resp
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = run_async(svc._collect_regtech_data(force=False))
        assert result["success"] is False

    def test_collect_regtech_data_connection_error(self):
        svc, _, _ = self._make_service()
        import requests as real_requests

        mock_requests = MagicMock()
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.ConnectionError = real_requests.ConnectionError
        mock_requests.post.side_effect = real_requests.ConnectionError("refused")
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = run_async(svc._collect_regtech_data(force=False))
        assert result["success"] is False

    def test_collect_regtech_data_general_exception(self):
        svc, _, _ = self._make_service()
        import requests as real_requests

        mock_requests = MagicMock()
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.ConnectionError = real_requests.ConnectionError
        mock_requests.RequestException = real_requests.RequestException
        mock_requests.post.side_effect = RuntimeError("boom")
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = run_async(svc._collect_regtech_data(force=False))
        assert result["success"] is False

    def test_collect_all_data(self):
        svc, _, _ = self._make_service()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"collected": 5}
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_resp
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = run_async(svc.collect_all_data(force=True))
        assert result["success"] is True

    # ---- sync_with_collector ----

    def test_sync_with_collector_success(self):
        svc, _, _ = self._make_service()
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
        svc, _, _ = self._make_service()
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

    # ---- force_schema_fix ----

    def test_force_schema_fix(self):
        svc, _, _ = self._make_service()
        svc.repo.add_column_if_not_exists = Mock(return_value=True)
        result = svc.force_schema_fix()
        assert result["success"] is True
        assert svc.repo.add_column_if_not_exists.call_count == 4

    # ---- force_data_refresh ----

    def test_force_data_refresh_success(self):
        svc, _, _ = self._make_service()
        svc.repo.deactivate_by_source = Mock()
        svc.repo.upsert_blacklist_from_collector = Mock()

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"ip_address": "1.1.1.1", "reason": "test", "country": "KR", "detection_date": "2024-01-01"}]
        }
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_resp
        mock_requests.RequestException = Exception
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = svc.force_data_refresh()
        assert result.get("success") is True or "copied_count" in result

    def test_force_data_refresh_non_200(self):
        svc, _, _ = self._make_service()
        mock_resp = Mock()
        mock_resp.status_code = 500
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_resp
        mock_requests.RequestException = Exception
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = svc.force_data_refresh()
        assert result["success"] is False
        assert result["fallback_attempted"] is True

    def test_force_data_refresh_request_exception(self):
        svc, _, _ = self._make_service()
        import requests as real_requests

        mock_requests = MagicMock()
        mock_requests.RequestException = real_requests.RequestException
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.get.side_effect = real_requests.RequestException("timeout")
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = svc.force_data_refresh()
        assert result["success"] is False
        assert result["fallback_attempted"] is True

    # ---- _copy_data_from_collector ----

    def test_copy_data_from_collector_with_data(self):
        svc, _, _ = self._make_service()
        svc.repo.deactivate_by_source = Mock()
        svc.repo.upsert_blacklist_from_collector = Mock()
        data = {
            "data": [
                {"ip_address": "1.1.1.1", "reason": "test", "country": "KR", "detection_date": "2024-01-01"},
                {"ip_address": "2.2.2.2", "reason": "malware", "country": "US", "detection_date": "2024-01-02"},
            ]
        }
        count = svc._copy_data_from_collector(data)
        assert count == 2
        assert svc.repo.upsert_blacklist_from_collector.call_count == 2

    def test_copy_data_from_collector_empty(self):
        svc, _, _ = self._make_service()
        svc.repo.deactivate_by_source = Mock()
        count = svc._copy_data_from_collector({"data": []})
        assert count == 0

    # ---- _fallback_direct_collection ----

    def test_fallback_direct_collection(self):
        svc, _, _ = self._make_service()
        result = svc._fallback_direct_collection()
        assert result["success"] is False
        assert result["fallback_attempted"] is True

    # ---- edge cases ----

    def test_add_to_blacklist_exception(self):
        svc, _, _ = self._make_service()
        svc.repo.insert_blacklist = Mock(side_effect=Exception("db error"))
        result = svc.add_to_blacklist("1.1.1.1", "test", "manual", 0.9)
        assert result is False

    def test_add_to_whitelist_exception(self):
        svc, _, _ = self._make_service()
        svc.repo.insert_whitelist = Mock(side_effect=Exception("db error"))
        result = svc.add_to_whitelist("1.1.1.1", "trusted", "manual")
        assert result is False

    def test_check_blacklist_redis_write_error(self):
        svc, _, mock_redis = self._make_service()
        svc.repo.check_whitelist = Mock(return_value=False)
        mock_redis.get.return_value = None
        svc.repo.get_blacklist_entry = Mock(
            return_value={
                "ip_address": "1.1.1.1",
                "reason": "malware",
                "source": "REGTECH",
                "is_active": True,
                "last_seen": "2024-01-01",
                "detection_count": 5,
            }
        )
        mock_redis.setex.side_effect = Exception("Redis write error")
        result = svc.check_blacklist("1.1.1.1")
        assert result["blocked"] is True

    def test_check_blacklist_general_exception(self):
        svc, _, mock_redis = self._make_service()
        svc.repo.check_whitelist = Mock(side_effect=Exception("boom"))
        result = svc.check_blacklist("1.1.1.1")
        assert result["blocked"] is False

    def test_get_collection_status_exception(self):
        svc, _, _ = self._make_service()
        svc.repo.get_source_summary = Mock(side_effect=Exception("db error"))
        result = svc.get_collection_status()
        assert result["collection_enabled"] is False
        assert "error" in result

    def test_get_health_redis_degraded(self):
        svc, _, mock_redis = self._make_service()
        mock_redis.ping.side_effect = Exception("connection refused")
        result = svc.get_health()
        assert result.status == "degraded"

    def test_create_whitelist_table(self):
        svc, _, _ = self._make_service()
        svc.repo.create_whitelist_table = Mock()
        svc._create_whitelist_table()
        svc.repo.create_whitelist_table.assert_called_once()
