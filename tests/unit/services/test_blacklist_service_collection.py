from unittest.mock import MagicMock, Mock, patch

from .blacklist_service_extended_cases import make_service, run_async


class TestBlacklistServiceCollection:
    def test_enable_collection(self):
        svc, _, _ = make_service()
        result = run_async(svc.enable_collection())
        assert result["success"] is True

    def test_disable_collection(self):
        svc, _, _ = make_service()
        result = run_async(svc.disable_collection())
        assert result["success"] is True

    def test_collect_regtech_data_success(self):
        svc, _, _ = make_service()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"collected": 10}

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_resp
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = run_async(svc._collect_regtech_data(force=True))
        assert result["success"] is True
        assert mock_requests.post.call_args.kwargs["timeout"] == 360

    def test_collect_regtech_data_non_200(self):
        svc, _, _ = make_service()
        mock_resp = Mock()
        mock_resp.status_code = 500

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_resp
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = run_async(svc._collect_regtech_data(force=False))
        assert result["success"] is False

    def test_collect_regtech_data_connection_error(self):
        svc, _, _ = make_service()
        import requests as real_requests

        mock_requests = MagicMock()
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.ConnectionError = real_requests.ConnectionError
        mock_requests.post.side_effect = real_requests.ConnectionError("refused")
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = run_async(svc._collect_regtech_data(force=False))
        assert result["success"] is False

    def test_collect_regtech_data_general_exception(self):
        svc, _, _ = make_service()
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
        svc, _, _ = make_service()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"collected": 5}
        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_resp
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = run_async(svc.collect_all_data(force=True))
        assert result["success"] is True

    def test_force_data_refresh_success(self):
        svc, _, _ = make_service()
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
        svc, _, _ = make_service()
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
        svc, _, _ = make_service()
        import requests as real_requests

        mock_requests = MagicMock()
        mock_requests.RequestException = real_requests.RequestException
        mock_requests.exceptions = real_requests.exceptions
        mock_requests.get.side_effect = real_requests.RequestException("timeout")
        with patch("core.services.blacklist_service.requests", mock_requests):
            result = svc.force_data_refresh()
        assert result["success"] is False
        assert result["fallback_attempted"] is True

    def test_copy_data_from_collector_with_data(self):
        svc, _, _ = make_service()
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
        svc, _, _ = make_service()
        svc.repo.deactivate_by_source = Mock()
        count = svc._copy_data_from_collector({"data": []})
        assert count == 0

    def test_fallback_direct_collection(self):
        svc, _, _ = make_service()
        result = svc._fallback_direct_collection()
        assert result["success"] is False
        assert result["fallback_attempted"] is True
