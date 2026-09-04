import importlib
from unittest.mock import MagicMock, Mock, patch

from .blacklist_service_extended_cases import make_service, run_async


class TestBlacklistServiceErrors:
    def test_add_to_blacklist_exception(self):
        svc, _, _ = make_service()
        svc.repo.insert_blacklist = Mock(side_effect=Exception("db error"))
        result = svc.add_to_blacklist("1.1.1.1", "test", "manual", 0.9)
        assert result is False

    def test_add_to_whitelist_exception(self):
        svc, _, _ = make_service()
        svc.repo.insert_whitelist = Mock(side_effect=Exception("db error"))
        result = svc.add_to_whitelist("1.1.1.1", "trusted", "manual")
        assert result is False

    def test_check_blacklist_redis_write_error(self):
        svc, _, mock_redis = make_service()
        svc.repo.count_whitelist_by_ip = Mock(return_value=0)
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
        svc, _, mock_redis = make_service()
        mock_redis.get.return_value = None
        svc.repo.count_whitelist_by_ip = Mock(side_effect=Exception("boom"))
        svc.repo.get_blacklist_entry = Mock(return_value=None)
        result = svc.check_blacklist("1.1.1.1")
        assert result["blocked"] is False
        svc.repo.count_whitelist_by_ip.assert_called_once_with("1.1.1.1")

    def test_get_collection_status_exception(self):
        svc, _, _ = make_service()
        svc.repo.get_source_stats = Mock(side_effect=Exception("db error"))
        result = svc.get_collection_status()
        assert result["collection_enabled"] is False
        assert "error" in result
        svc.repo.get_source_stats.assert_called_once_with()

    def test_get_health_redis_degraded(self):
        svc, _, mock_redis = make_service()
        mock_redis.ping.side_effect = Exception("connection refused")
        result = svc.get_health()
        assert result.status == "degraded"

    def test_runtime_schema_creation_is_not_exposed(self):
        svc, _, _ = make_service()
        assert not hasattr(svc, "_create_whitelist_table")

    def test_requests_patch_follows_each_service_import_path(self):
        core_module = importlib.import_module("core.services.blacklist_service")
        app_module = importlib.import_module("app.core.services.blacklist_service")
        core_service = object.__new__(core_module.BlacklistService)
        app_service = object.__new__(app_module.BlacklistService)

        core_response = Mock(status_code=200)
        core_response.json.return_value = {"collected": 1}
        app_response = Mock(status_code=200)
        app_response.json.return_value = {"collected": 2}
        core_requests = MagicMock()
        core_requests.post.return_value = core_response
        core_requests.get.return_value = Mock(status_code=200)
        app_requests = MagicMock()
        app_requests.post.return_value = app_response
        app_requests.get.return_value = Mock(status_code=200)

        core_service.get_system_stats = Mock(return_value={"total_ips": 1, "active_ips": 1})
        app_service.get_system_stats = Mock(return_value={"total_ips": 2, "active_ips": 2})
        with patch.object(core_module, "requests", core_requests), patch.object(app_module, "requests", app_requests):
            core_result = run_async(core_service._collect_regtech_data())
            app_result = run_async(app_service._collect_regtech_data())
            core_sync = core_service.sync_with_collector()
            app_sync = app_service.sync_with_collector()

        assert core_result["collected"] == 1
        assert app_result["collected"] == 2
        assert core_sync["total_ips"] == 1
        assert app_sync["total_ips"] == 2
        core_requests.post.assert_called_once()
        app_requests.post.assert_called_once()
        core_requests.get.assert_called_once()
        app_requests.get.assert_called_once()
