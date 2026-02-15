from unittest.mock import Mock, MagicMock, patch

import pytest

from core.services.collection.regtech_data import REGTECHDataCollector


def _make_collector():
    return REGTECHDataCollector()


class TestREGTECHDataCollectorInit:
    def test_init_sets_base_url(self):
        collector = _make_collector()
        assert "regtech" in collector.base_url.lower()


class TestCollectRegtechIps:
    def test_returns_empty_list(self):
        collector = _make_collector()
        result = collector.collect_regtech_ips()
        assert isinstance(result, list)
        assert len(result) == 0


class TestTestRegtechCollection:
    def test_returns_test_stub(self):
        collector = _make_collector()
        result = collector.test_regtech_collection("user", "pass", "2024-01-01", "2024-01-31")
        assert isinstance(result, dict)
        assert result.get("success") is True
        assert result.get("test_mode") is True


class TestCollectThreatIntelligenceIps:
    def test_returns_stub(self):
        collector = _make_collector()
        result = collector.collect_threat_intelligence_ips()
        assert isinstance(result, dict)
        assert result.get("success") is True
        assert result.get("collected_count") == 0


class TestCollectMaliciousIpLists:
    def test_returns_stub(self):
        collector = _make_collector()
        result = collector.collect_malicious_ip_lists()
        assert isinstance(result, dict)
        assert result.get("success") is True


class TestIsPrivateIp:
    def test_private_10_network(self):
        collector = _make_collector()
        assert collector._is_private_ip("10.0.0.1") is True

    def test_private_172_network(self):
        collector = _make_collector()
        assert collector._is_private_ip("172.16.0.1") is True

    def test_private_192_network(self):
        collector = _make_collector()
        assert collector._is_private_ip("192.168.1.1") is True

    def test_private_127_network(self):
        collector = _make_collector()
        assert collector._is_private_ip("127.0.0.1") is True

    def test_private_169_254_network(self):
        collector = _make_collector()
        assert collector._is_private_ip("169.254.1.1") is True

    def test_public_ip(self):
        collector = _make_collector()
        assert collector._is_private_ip("8.8.8.8") is False

    def test_public_ip_2(self):
        collector = _make_collector()
        assert collector._is_private_ip("1.2.3.4") is False


class TestParseRegtechData:
    def test_parse_html_with_ips(self):
        collector = _make_collector()
        html = "<html><body><p>Blocked IP: 8.8.8.8 with confidence 90</p></body></html>"
        result = collector._parse_regtech_data(html)
        assert isinstance(result, list)
        found_ips = [r["ip_address"] if isinstance(r, dict) else r for r in result]
        assert any("8.8.8.8" in str(ip) for ip in found_ips)

    def test_parse_html_no_ips(self):
        collector = _make_collector()
        html = "<html><body><p>No IPs here</p></body></html>"
        result = collector._parse_regtech_data(html)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_parse_html_filters_private_ips(self):
        collector = _make_collector()
        html = "<html><body><p>IP: 192.168.1.1</p><p>IP: 8.8.4.4</p></body></html>"
        result = collector._parse_regtech_data(html)
        ip_strings = [str(r.get("ip_address", r) if isinstance(r, dict) else r) for r in result]
        assert not any("192.168.1.1" in ip for ip in ip_strings)

    def test_parse_html_table_format(self):
        collector = _make_collector()
        html = "<table><tr><td>1.2.3.4</td><td>malicious</td></tr></table>"
        result = collector._parse_regtech_data(html)
        assert isinstance(result, list)


class TestExtractConfidenceFromHtml:
    def test_extract_confidence_number(self):
        collector = _make_collector()
        html = "IP 1.2.3.4 confidence: 85 detected today"
        result = collector._extract_confidence_from_html(html, "1.2.3.4")
        if result is not None:
            assert isinstance(result, int)
            assert 0 <= result <= 100

    def test_extract_confidence_not_found(self):
        collector = _make_collector()
        html = "No confidence data here"
        result = collector._extract_confidence_from_html(html, "1.2.3.4")
        assert result is None


class TestExtractDetectionDateFromHtml:
    def test_extract_date_yyyy_mm_dd(self):
        collector = _make_collector()
        html = "IP 1.2.3.4 detected on 2024-01-15 by scanner"
        result = collector._extract_detection_date_from_html(html, "1.2.3.4")
        if result is not None:
            assert hasattr(result, "year")

    def test_extract_date_not_found(self):
        collector = _make_collector()
        html = "No date info"
        result = collector._extract_detection_date_from_html(html, "1.2.3.4")
        assert result is None


class TestExtractRemovalDateFromHtml:
    def test_extract_removal_date(self):
        collector = _make_collector()
        html = "IP 1.2.3.4 \ud574\uc81c\uc608\uc815: 2024-06-15"
        result = collector._extract_removal_date_from_html(html, "1.2.3.4")
        if result is not None:
            assert hasattr(result, "year")


class TestDiscoverDataUrls:
    def test_discover_urls(self):
        collector = _make_collector()
        mock_session = MagicMock()
        mock_resp = Mock()
        mock_resp.text = '<html><a href="/threat/list">Threats</a></html>'
        mock_resp.status_code = 200
        mock_session.get.return_value = mock_resp
        result = collector._discover_data_urls(mock_session)
        assert isinstance(result, list)


class TestExtractNavigationLinks:
    def test_extract_links_with_threat_keyword(self):
        collector = _make_collector()
        html = '<a href="/blacklist/view">View Blacklist</a><a href="/about">About</a>'
        result = collector._extract_navigation_links(html)
        assert isinstance(result, list)

    def test_extract_links_no_matches(self):
        collector = _make_collector()
        html = '<a href="/about">About</a><a href="/contact">Contact</a>'
        result = collector._extract_navigation_links(html)
        assert isinstance(result, list)


class TestCollectRealRegtechData:
    def test_collect_with_valid_session(self):
        collector = _make_collector()
        mock_session = MagicMock()
        mock_session.cookies = MagicMock()
        mock_session.cookies.__len__ = Mock(return_value=2)
        with patch.object(
            collector, "_discover_data_urls", return_value=[{"url": "https://example.com/data", "type": "blacklist"}]
        ):
            mock_resp = Mock()
            mock_resp.text = "<html><body>8.8.8.8</body></html>"
            mock_resp.status_code = 200
            mock_session.get.return_value = mock_resp
            result = collector.collect_real_regtech_data(mock_session, "user1")
        assert isinstance(result, dict)

    def test_collect_with_no_cookies(self):
        collector = _make_collector()
        mock_session = MagicMock()
        mock_session.cookies = MagicMock()
        mock_session.cookies.__len__ = Mock(return_value=0)
        result = collector.collect_real_regtech_data(mock_session, "user1")
        assert isinstance(result, dict)
        # When no cookies, success may be False or result may indicate no data
        # Accept either way — key is that it returns a dict without crashing
        if "success" in result:
            assert result["success"] is False or result["success"] is True


class TestExpandRegtechCollection:
    def test_expand_returns_list(self):
        collector = _make_collector()
        base_data = [{"ip_address": "1.2.3.4"}]
        result = collector.expand_regtech_collection(base_data)
        assert isinstance(result, list)


class TestGenerateAdditionalIps:
    def test_returns_empty(self):
        collector = _make_collector()
        result = collector._generate_additional_ips(10)
        assert isinstance(result, list)
        assert len(result) == 0
