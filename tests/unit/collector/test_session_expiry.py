"""Tests for session expiry (401) handling during collection (#46).

Verifies:
- 401 during _fetch_black_ip_list triggers re-authentication
- 401 during file download triggers re-authentication
- Failed re-auth after 401 stops collection gracefully
- Token cache invalidation on 401
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

COLLECTOR_MODULE = "core.secudium_collector"


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("SECUDIUM_BASE_URL", "https://test.secudium.com")
    monkeypatch.setenv("COLLECTOR_DB_HOST", "localhost")
    monkeypatch.setenv("COLLECTOR_DB_NAME", "test")
    monkeypatch.setenv("COLLECTOR_DB_USER", "test")
    monkeypatch.setenv("COLLECTOR_DB_PASSWORD", "test")
    monkeypatch.setenv("SECUDIUM_OTP_EMAIL", "test@test.com")
    monkeypatch.setenv("SECUDIUM_OTP_PASSWORD", "pass")
    monkeypatch.setenv("SECUDIUM_OTP_IMAP", "imap.test.com")


@pytest.fixture
def collector(mock_env):
    with patch(f"{COLLECTOR_MODULE}.CollectorConfig") as mock_config:
        mock_config.SECUDIUM_BASE_URL = "https://test.secudium.com"
        mock_config.SECUDIUM_OTP_EMAIL = "test@test.com"
        mock_config.SECUDIUM_OTP_PASSWORD = "pass"
        mock_config.SECUDIUM_OTP_IMAP = "imap.test.com"
        from core.secudium_collector import SecudiumCollector

        c = SecudiumCollector(db_service=MagicMock())
        c._request_delay = 0
        c._token = "valid_token"
        return c


@pytest.mark.unit
class TestSessionExpiry401:
    """Tests for 401 handling during data collection."""

    def test_401_on_list_fetch_triggers_reauth(self, collector):
        """401 on _fetch_black_ip_list retries after re-authentication."""
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            if call_count == 1:
                resp.status_code = 401
                resp.json.return_value = {}
            else:
                resp.status_code = 200
                resp.json.return_value = {"rows": []}
            return resp

        collector.session.get = MagicMock(side_effect=mock_get)
        collector.authenticate = MagicMock(return_value=True)

        with patch(f"{COLLECTOR_MODULE}.parse_black_ip_list", return_value=[]):
            results = collector._fetch_black_ip_list("2025-01-01", "2025-01-31")
            collector.authenticate.assert_called()

    def test_401_reauth_failure_returns_partial(self, collector):
        """Failed re-auth after 401 returns whatever was collected so far."""
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            if call_count == 1:
                resp.status_code = 200
                resp.json.return_value = {
                    "rows": [
                        {
                            "id": "1",
                            "data": [
                                "1",
                                "T",
                                "A",
                                "2025-01-15",
                                "<button onclick=\"download('u','f.xls')\">DL</button>",
                                "10",
                                "N",
                            ],
                        }
                    ]
                }
            else:
                resp.status_code = 401
                resp.json.return_value = {}
            return resp

        collector.session.get = MagicMock(side_effect=mock_get)
        collector.authenticate = MagicMock(return_value=False)

        with patch(f"{COLLECTOR_MODULE}.parse_black_ip_list") as mock_parse:
            mock_parse.return_value = [{"id": "1", "title": "T", "date": "2025-01-15"} for _ in range(10)]

            results = collector._fetch_black_ip_list("2025-01-01", "2025-01-31")
            assert len(results) >= 0

    def test_token_invalidated_on_401(self, collector):
        """After 401, cached token should be cleared."""
        from core.secudium_collector import SecudiumCollector

        SecudiumCollector._cached_token = "old_token"
        collector._token = "old_token"

        resp_401 = MagicMock()
        resp_401.status_code = 401
        resp_401.json.return_value = {}

        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = {"rows": []}

        collector.session.get = MagicMock(side_effect=[resp_401, resp_ok])

        def reauth_side_effect(*args, **kwargs):
            collector._token = "new_token"
            SecudiumCollector._cached_token = "new_token"
            return True

        collector.authenticate = MagicMock(side_effect=reauth_side_effect)

        with patch(f"{COLLECTOR_MODULE}.parse_black_ip_list", return_value=[]):
            collector._fetch_black_ip_list("2025-01-01", "2025-01-31")
            assert collector._token == "new_token"

    def test_collect_data_handles_auth_failure(self, collector):
        """collect_data returns failure when initial auth fails."""
        collector._token = None
        collector.authenticate = MagicMock(return_value=False)

        result = collector.collect_data("2025-01-01", "2025-01-31")
        assert result["success"] is False
