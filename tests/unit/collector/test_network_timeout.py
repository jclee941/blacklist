"""Tests for network timeout and abnormal response handling (#47).

Verifies:
- Connection timeout during API calls
- Read timeout during API calls
- Non-JSON response handling
- HTTP 500 error handling
- Malformed response body handling
"""

import pytest
import requests
from unittest.mock import MagicMock, patch

COLLECTOR_MODULE = "core.secudium_collector"


@pytest.fixture
def collector():
    with patch(f"{COLLECTOR_MODULE}.CollectorConfig") as mock_config:
        mock_config.SECUDIUM_BASE_URL = "https://test.secudium.com"
        mock_config.get_secudium_otp_config.return_value = {
            "email": "test@test.com",
            "email_password": "pass",
            "imap_server": "imap.test.com",
            "otp_mode": "manual",
        }
        from core.secudium_collector import SecudiumCollector

        c = SecudiumCollector(db_service=MagicMock())
        c._request_delay = 0
        c._token = "valid_token"
        return c


@pytest.mark.unit
class TestConnectionTimeout:
    """Tests for connection timeout scenarios."""

    def test_login_connection_timeout(self, collector):
        """Connection timeout during login returns 'failed'."""
        collector.session.post = MagicMock(side_effect=requests.exceptions.ConnectTimeout("Connection timed out"))

        result = collector._login("user", "pass", False, "")
        assert result == "failed"

    def test_login_read_timeout(self, collector):
        """Read timeout during login returns 'failed'."""
        collector.session.post = MagicMock(side_effect=requests.exceptions.ReadTimeout("Read timed out"))

        with patch("time.sleep"):
            result = collector._login("user", "pass", False, "")
        assert result == "failed"

    def test_login_generic_connection_error(self, collector):
        """Generic ConnectionError during login returns 'failed'."""
        collector.session.post = MagicMock(side_effect=requests.exceptions.ConnectionError("Connection refused"))

        result = collector._login("user", "pass", False, "")
        assert result == "failed"


@pytest.mark.unit
class TestAbnormalResponses:
    """Tests for non-standard HTTP responses."""

    def test_500_error_on_list_fetch(self, collector):
        """HTTP 500 during list fetch is handled gracefully."""
        resp = MagicMock()
        resp.status_code = 500
        resp.text = "Internal Server Error"
        resp.json.side_effect = ValueError("No JSON")
        collector.session.get = MagicMock(return_value=resp)

        with patch(f"{COLLECTOR_MODULE}.parse_black_ip_list", return_value=[]):
            results = collector._fetch_black_ip_list("2025-01-01", "2025-01-31")
            assert isinstance(results, list)

    def test_non_json_response_on_login(self, collector):
        """Non-JSON response body during login is handled."""
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "<html>Maintenance page</html>"
        resp.json.side_effect = ValueError("Not JSON")
        resp.cookies = {}
        resp.headers = {}
        collector.session.post = MagicMock(return_value=resp)

        result = collector._login("user", "pass", False, "")
        assert result in ("failed", "otp_required")

    def test_empty_response_body(self, collector):
        """Empty response body on login is handled."""
        resp = MagicMock()
        resp.status_code = 200
        resp.text = ""
        resp.json.side_effect = ValueError("Empty")
        resp.cookies = {}
        resp.headers = {}
        collector.session.post = MagicMock(return_value=resp)

        result = collector._login("user", "pass", False, "")
        assert result == "failed"

    def test_malformed_json_response(self, collector):
        """Malformed JSON in list response is handled."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"unexpected_key": "value"}
        collector.session.get = MagicMock(return_value=resp)

        with patch(f"{COLLECTOR_MODULE}.parse_black_ip_list", return_value=[]):
            results = collector._fetch_black_ip_list("2025-01-01", "2025-01-31")
            assert results == []


@pytest.mark.unit
class TestDownloadErrors:
    """Tests for file download error scenarios."""

    def test_timeout_on_file_download(self, collector):
        """Timeout during XLS download returns empty results."""
        collector.session.get = MagicMock(side_effect=requests.exceptions.Timeout("Download timed out"))

        result = collector._download_and_parse("server_uuid", "test.xls", "Title", "2025-01-15")
        assert result == []

    def test_connection_error_on_download(self, collector):
        """Connection error during download returns empty results."""
        collector.session.get = MagicMock(side_effect=requests.exceptions.ConnectionError("Network unreachable"))

        result = collector._download_and_parse("server_uuid", "test.xls", "Title", "2025-01-15")
        assert result == []

    def test_http_error_on_download(self, collector):
        """HTTP error (404) on file download returns empty results."""
        resp = MagicMock()
        resp.status_code = 404
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError("Not Found")
        collector.session.get = MagicMock(return_value=resp)

        result = collector._download_and_parse("server_uuid", "test.xls", "Title", "2025-01-15")
        assert result == []
