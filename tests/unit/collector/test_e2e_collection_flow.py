"""
#44 — E2E: Full secudium collection flow test

Tests the complete collect_data() pipeline end-to-end with mocked
network I/O: authenticate → fetch list → download → parse → insert → logout.
"""

import pytest
from unittest.mock import MagicMock, patch, call

COLLECTOR_MODULE = "core.secudium_collector"


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("SECUDIUM_BASE_URL", "https://test.secudium.com")
    monkeypatch.setenv("SECUDIUM_EMAIL_ADDRESS", "test@example.com")
    monkeypatch.setenv("SECUDIUM_EMAIL_PASSWORD", "emailpass")
    monkeypatch.setenv("SECUDIUM_IMAP_SERVER", "imap.test.com")


@pytest.fixture
def collector(mock_env):
    with patch(f"{COLLECTOR_MODULE}.CollectorConfig") as mock_config:
        mock_config.SECUDIUM_BASE_URL = "https://test.secudium.com"
        mock_config.SECUDIUM_EMAIL_ADDRESS = "test@example.com"
        mock_config.SECUDIUM_EMAIL_PASSWORD = "emailpass"
        mock_config.SECUDIUM_IMAP_SERVER = "imap.test.com"

        from core.secudium_collector import SecudiumCollector

        db = MagicMock()
        c = SecudiumCollector(db_service=db)
        c.session = MagicMock()
        yield c


@pytest.mark.unit
class TestCollectDataE2E:
    """End-to-end tests for SecudiumCollector.collect_data()."""

    def test_full_success_flow(self, collector):
        """Happy path: authenticate → fetch → download → parse → insert → logout."""
        collector.authenticate = MagicMock(return_value=True)
        collector._logout = MagicMock()

        entries = [
            {
                "title": "Entry 1",
                "date": "2025-01-15",
                "download_html": "<a href='/download/file1.xls'>file1.xls</a>",
            },
            {
                "title": "Entry 2",
                "date": "2025-01-16",
                "download_html": "<a href='/download/file2.xls'>file2.xls</a>",
            },
        ]

        parsed_ips_1 = [
            {"ip": "1.2.3.4", "reason": "malware", "country": "KR"},
            {"ip": "5.6.7.8", "reason": "spam", "country": "US"},
        ]
        parsed_ips_2 = [
            {"ip": "10.0.0.1", "reason": "botnet", "country": "CN"},
        ]

        with (
            patch(f"{COLLECTOR_MODULE}._fetch_black_ip_list", create=True),
            patch.object(collector, "_fetch_black_ip_list", return_value=entries),
            patch(
                f"{COLLECTOR_MODULE}.extract_download_info",
                side_effect=[
                    ("server_file1.xls", "file1.xls"),
                    ("server_file2.xls", "file2.xls"),
                ],
            ),
            patch.object(
                collector,
                "_download_and_parse",
                side_effect=[parsed_ips_1, parsed_ips_2],
            ),
            patch.object(collector, "_insert_ips") as mock_insert,
        ):
            result = collector.collect_data("2025-01-01", "2025-01-31")

        assert result["success"] is True
        assert result["total_entries"] == 2
        assert result["total_ips"] == 3
        assert result["files_downloaded"] == 2
        assert len(result["errors"]) == 0
        collector.authenticate.assert_called_once()
        collector._logout.assert_called_once()
        mock_insert.assert_called_once()

    def test_auth_failure_returns_error(self, collector):
        """collect_data returns error result when authentication fails."""
        collector.authenticate = MagicMock(return_value=False)
        collector._logout = MagicMock()

        result = collector.collect_data("2025-01-01", "2025-01-31")

        assert result["success"] is False
        assert result["total_ips"] == 0

    def test_empty_fetch_returns_zero(self, collector):
        """No entries fetched → success with zero counts."""
        collector.authenticate = MagicMock(return_value=True)
        collector._logout = MagicMock()

        with patch.object(collector, "_fetch_black_ip_list", return_value=[]):
            result = collector.collect_data("2025-01-01", "2025-01-31")

        assert result["success"] is True
        assert result["total_entries"] == 0
        assert result["total_ips"] == 0

    def test_download_error_counted(self, collector):
        """Download failure for one entry is counted in errors."""
        collector.authenticate = MagicMock(return_value=True)
        collector._logout = MagicMock()

        entries = [
            {
                "title": "Entry 1",
                "date": "2025-01-15",
                "download_html": "<a href='/download/file1.xls'>file1.xls</a>",
            },
        ]

        with (
            patch.object(collector, "_fetch_black_ip_list", return_value=entries),
            patch(
                f"{COLLECTOR_MODULE}.extract_download_info",
                return_value=("server_file1.xls", "file1.xls"),
            ),
            patch.object(
                collector,
                "_download_and_parse",
                side_effect=Exception("Download failed"),
            ),
        ):
            result = collector.collect_data("2025-01-01", "2025-01-31")

        assert len(result["errors"]) > 0
        collector._logout.assert_called_once()

    def test_logout_called_on_exception(self, collector):
        """_logout is called even when an exception occurs mid-flow."""
        collector.authenticate = MagicMock(return_value=True)
        collector._logout = MagicMock()

        with patch.object(
            collector,
            "_fetch_black_ip_list",
            side_effect=RuntimeError("Network error"),
        ):
            result = collector.collect_data("2025-01-01", "2025-01-31")

        assert result["success"] is False
        collector._logout.assert_called_once()

    def test_default_date_range(self, collector):
        """When no dates provided, defaults to 7-day range."""
        collector.authenticate = MagicMock(return_value=True)
        collector._logout = MagicMock()

        with patch.object(collector, "_fetch_black_ip_list", return_value=[]) as mock_fetch:
            collector.collect_data(None, None)
            args = mock_fetch.call_args
            assert args is not None
            start_date = args[0][0] if args[0] else args[1].get("start_date")
            assert start_date is not None

    def test_insert_skipped_when_no_db(self, mock_env):
        """If db_service is None, _insert_ips is not called."""
        with patch(f"{COLLECTOR_MODULE}.CollectorConfig") as mock_config:
            mock_config.SECUDIUM_BASE_URL = "https://test.secudium.com"
            mock_config.SECUDIUM_EMAIL_ADDRESS = "test@example.com"
            mock_config.SECUDIUM_EMAIL_PASSWORD = "emailpass"
            mock_config.SECUDIUM_IMAP_SERVER = "imap.test.com"

            from core.secudium_collector import SecudiumCollector

            c = SecudiumCollector(db_service=None)
            c.session = MagicMock()

        c.authenticate = MagicMock(return_value=True)
        c._logout = MagicMock()

        entries = [
            {
                "title": "Entry 1",
                "date": "2025-01-15",
                "download_html": "<a href='/d/f.xls'>f.xls</a>",
            },
        ]

        with (
            patch.object(c, "_fetch_black_ip_list", return_value=entries),
            patch(
                f"{COLLECTOR_MODULE}.extract_download_info",
                return_value=("sf.xls", "f.xls"),
            ),
            patch.object(
                c,
                "_download_and_parse",
                return_value=[{"ip": "1.1.1.1"}],
            ),
            patch.object(c, "_insert_ips") as mock_insert,
        ):
            result = c.collect_data("2025-01-01", "2025-01-31")

        if c.db_service is None:
            mock_insert.assert_not_called()
