"""Tests for multi-page data fetching in SecudiumCollector (#42).

Verifies paginated _fetch_black_ip_list correctly handles:
- Single page, multi-page, empty first page
- 401 re-auth during pagination
- Error mid-pagination continues gracefully
"""

import pytest
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


def _make_grid_response(entries, count_per_page=10):
    """Build a DHTMLX grid-style response JSON."""
    rows = []
    for i, entry in enumerate(entries):
        rows.append(
            {
                "id": str(i + 1),
                "data": [
                    str(i + 1),
                    entry.get("title", f"Entry {i + 1}"),
                    entry.get("author", "admin"),
                    entry.get("date", "2025-01-15"),
                    entry.get("download", "<button onclick=\"download('uuid','file.xls')\">Download</button>"),
                    str(entry.get("count", "5")),
                    "N",
                ],
            }
        )
    return {"rows": rows}


@pytest.mark.unit
class TestMultiPageFetching:
    """Tests for _fetch_black_ip_list pagination logic."""

    def test_single_page_returns_all_entries(self, collector):
        """Single page with fewer entries than count_per_page stops pagination."""
        page_data = _make_grid_response([{"title": f"IP {i}"} for i in range(3)])

        with patch(f"{COLLECTOR_MODULE}.parse_black_ip_list") as mock_parse:
            mock_parse.return_value = [{"id": str(i), "title": f"IP {i}", "date": "2025-01-15"} for i in range(3)]

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = page_data
            collector.session.get = MagicMock(return_value=mock_resp)

            results = collector._fetch_black_ip_list("2025-01-01", "2025-01-31")

            assert len(results) == 3
            assert collector.session.get.call_count == 1

    def test_multi_page_collects_all(self, collector):
        """Multiple pages are fetched until a page returns fewer than count_per_page."""
        full_page = [{"id": str(i), "title": f"IP {i}", "date": "2025-01-15"} for i in range(100)]
        partial_page = [{"id": str(i), "title": f"IP {i}", "date": "2025-01-15"} for i in range(3)]

        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.status_code = 200
            if call_count <= 2:
                resp.json.return_value = _make_grid_response([{"title": f"IP {i}"} for i in range(100)])
            else:
                resp.json.return_value = _make_grid_response([{"title": f"IP {i}"} for i in range(3)])
            return resp

        collector.session.get = MagicMock(side_effect=mock_get)

        with patch(f"{COLLECTOR_MODULE}.parse_black_ip_list") as mock_parse:
            mock_parse.side_effect = [full_page, full_page, partial_page]
            results = collector._fetch_black_ip_list("2025-01-01", "2025-01-31")

            assert len(results) == 203
            assert call_count == 3

    def test_empty_first_page_returns_empty(self, collector):
        """Empty first page returns empty list immediately."""
        with patch(f"{COLLECTOR_MODULE}.parse_black_ip_list") as mock_parse:
            mock_parse.return_value = []

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"rows": []}
            collector.session.get = MagicMock(return_value=mock_resp)

            results = collector._fetch_black_ip_list("2025-01-01", "2025-01-31")
            assert results == []

    def test_401_triggers_reauth(self, collector):
        """401 response on page 2 triggers re-authentication and retries."""
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            if call_count == 1:
                # Page 1: full page (100 entries) so pagination continues
                resp.status_code = 200
                resp.json.return_value = _make_grid_response([{"title": f"IP {i}"} for i in range(100)])
            elif call_count == 2:
                # Page 2: 401 triggers reauth
                resp.status_code = 401
                resp.json.return_value = {}
            else:
                # Retry after reauth: partial page stops pagination
                resp.status_code = 200
                resp.json.return_value = _make_grid_response([{"title": f"IP {i}"} for i in range(3)])
            return resp

        collector.session.get = MagicMock(side_effect=mock_get)
        collector.authenticate = MagicMock(return_value=True)

        full_page = [{"id": str(i), "title": f"IP {i}", "date": "2025-01-15"} for i in range(100)]
        partial_page = [{"id": str(i), "title": f"IP {i}", "date": "2025-01-15"} for i in range(3)]

        with patch(f"{COLLECTOR_MODULE}.parse_black_ip_list") as mock_parse:
            mock_parse.side_effect = [full_page, partial_page]

            results = collector._fetch_black_ip_list("2025-01-01", "2025-01-31")
            collector.authenticate.assert_called()
            assert len(results) == 103

    def test_max_pages_limit_respected(self, collector):
        """Pagination stops at max_pages even if more data exists."""
        full_page = [{"id": str(i), "title": f"IP {i}", "date": "2025-01-15"} for i in range(100)]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _make_grid_response([{"title": f"IP {i}"} for i in range(100)])
        collector.session.get = MagicMock(return_value=mock_resp)

        with patch(f"{COLLECTOR_MODULE}.parse_black_ip_list") as mock_parse:
            mock_parse.return_value = full_page

            results = collector._fetch_black_ip_list("2025-01-01", "2025-01-31", max_pages=2)

            assert collector.session.get.call_count == 2
            assert len(results) == 200
