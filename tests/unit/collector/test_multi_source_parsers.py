"""Tests for MultiSourceParserMixin from core/multi_source/parsers.py."""

import pytest

from core.multi_source.parsers import MultiSourceParserMixin
from core.multi_source.models import SourceConfig, SourceType


class ParserHost(MultiSourceParserMixin):
    pass


@pytest.fixture
def parser():
    return ParserHost()


@pytest.fixture
def config():
    return SourceConfig(
        source_type=SourceType.ABUSE_CH,
        name="TestSource",
        url="https://example.com",
    )


class TestIsValidIp:
    def test_public_ip(self, parser):
        assert parser._is_valid_ip("8.8.8.8") is True

    def test_private_ip(self, parser):
        assert parser._is_valid_ip("192.168.1.1") is False

    def test_loopback(self, parser):
        assert parser._is_valid_ip("127.0.0.1") is False

    def test_multicast(self, parser):
        assert parser._is_valid_ip("224.0.0.1") is False

    def test_empty_string(self, parser):
        assert parser._is_valid_ip("") is False

    def test_invalid_format(self, parser):
        assert parser._is_valid_ip("not-an-ip") is False

    def test_whitespace_stripped(self, parser):
        assert parser._is_valid_ip("  8.8.8.8  ") is True


class TestDetermineCategoryFromThreatType:
    def test_botnet(self, parser):
        assert parser._determine_category_from_threat_type("Botnet C2") == "botnet"

    def test_c2_command(self, parser):
        assert parser._determine_category_from_threat_type("Command and Control") == "botnet"

    def test_phishing(self, parser):
        assert parser._determine_category_from_threat_type("Phishing URL") == "phishing"

    def test_malware(self, parser):
        assert parser._determine_category_from_threat_type("Trojan dropper") == "malware"

    def test_rat(self, parser):
        assert parser._determine_category_from_threat_type("RAT payload") == "malware"

    def test_spam(self, parser):
        assert parser._determine_category_from_threat_type("Spam campaign") == "spam"

    def test_default_malicious(self, parser):
        assert parser._determine_category_from_threat_type("Unknown threat") == "malicious"

    def test_empty_string(self, parser):
        assert parser._determine_category_from_threat_type("") == "malicious"


class TestParseTextFeed:
    def test_plain_ips(self, parser, config):
        text = "8.8.8.8\n1.1.1.1\n"
        result = parser._parse_text_feed(text, config, max_ips=100)
        assert result["success"] is True
        assert len(result["data"]) == 2
        assert result["data"][0]["ip_address"] == "8.8.8.8"

    def test_comments_skipped(self, parser, config):
        text = "# comment\n// another\n8.8.8.8"
        result = parser._parse_text_feed(text, config, max_ips=100)
        assert len(result["data"]) == 1

    def test_empty_lines_skipped(self, parser, config):
        text = "\n\n8.8.8.8\n\n"
        result = parser._parse_text_feed(text, config, max_ips=100)
        assert len(result["data"]) == 1

    def test_ip_port_format(self, parser, config):
        text = "8.8.8.8:443"
        result = parser._parse_text_feed(text, config, max_ips=100)
        assert result["data"][0]["ip_address"] == "8.8.8.8"

    def test_private_ip_excluded(self, parser, config):
        text = "192.168.1.1\n8.8.8.8"
        result = parser._parse_text_feed(text, config, max_ips=100)
        assert len(result["data"]) == 1

    def test_max_ips_respected(self, parser, config):
        text = "\n".join([f"1.2.3.{i}" for i in range(1, 50)])
        result = parser._parse_text_feed(text, config, max_ips=5)
        assert len(result["data"]) == 5

    def test_source_name_from_config(self, parser, config):
        text = "8.8.8.8"
        result = parser._parse_text_feed(text, config, max_ips=100)
        assert result["data"][0]["source"] == "TestSource"

    def test_url_line_extracts_host(self, parser, config):
        text = "http://8.8.8.8/malware.exe"
        result = parser._parse_text_feed(text, config, max_ips=100)
        assert len(result["data"]) == 1
        assert result["data"][0]["ip_address"] == "8.8.8.8"


class TestParseJsonFeed:
    def test_list_input(self, parser, config):
        data = [{"ip": "8.8.8.8"}, {"ip": "1.1.1.1"}]
        result = parser._parse_json_feed(data, config, max_ips=100)
        assert result["success"] is True
        assert len(result["data"]) == 2

    def test_dict_with_data_key(self, parser, config):
        data = {"data": [{"ip": "8.8.8.8"}]}
        result = parser._parse_json_feed(data, config, max_ips=100)
        assert len(result["data"]) == 1

    def test_dict_with_results_key(self, parser, config):
        data = {"results": [{"ip": "8.8.8.8"}]}
        result = parser._parse_json_feed(data, config, max_ips=100)
        assert len(result["data"]) == 1

    def test_private_ip_excluded(self, parser, config):
        data = [{"ip": "192.168.1.1"}, {"ip": "8.8.8.8"}]
        result = parser._parse_json_feed(data, config, max_ips=100)
        assert len(result["data"]) == 1

    def test_max_ips_respected(self, parser, config):
        data = [{"ip": f"1.2.3.{i}"} for i in range(1, 50)]
        result = parser._parse_json_feed(data, config, max_ips=3)
        assert len(result["data"]) == 3

    def test_custom_ip_field(self, parser):
        cfg = SourceConfig(
            source_type=SourceType.CUSTOM_API,
            name="Custom",
            url="https://example.com",
            ip_field="target",
        )
        data = [{"target": "8.8.8.8"}]
        result = parser._parse_json_feed(data, cfg, max_ips=100)
        assert len(result["data"]) == 1

    def test_non_dict_items_skipped(self, parser, config):
        data = ["not a dict", {"ip": "8.8.8.8"}, 42]
        result = parser._parse_json_feed(data, config, max_ips=100)
        assert len(result["data"]) == 1

    def test_empty_list(self, parser, config):
        result = parser._parse_json_feed([], config, max_ips=100)
        assert result["success"] is True
        assert len(result["data"]) == 0


class TestParseThreatfoxData:
    def test_valid_data(self, parser, config):
        data = {
            "query_status": "ok",
            "data": [
                {
                    "ioc": "8.8.8.8:443",
                    "ioc_type": "ip:port",
                    "threat_type": "botnet_cc",
                    "first_seen": "2026-01-01 12:00:00",
                    "malware": "Emotet",
                }
            ],
        }
        result = parser._parse_threatfox_data(data, config, max_ips=100)
        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["ip_address"] == "8.8.8.8"

    def test_query_status_not_ok(self, parser, config):
        data = {"query_status": "error", "data": []}
        result = parser._parse_threatfox_data(data, config, max_ips=100)
        assert result["success"] is True
        assert len(result["data"]) == 0

    def test_private_ip_excluded(self, parser, config):
        data = {
            "query_status": "ok",
            "data": [{"ioc": "192.168.1.1:80", "ioc_type": "ip:port"}],
        }
        result = parser._parse_threatfox_data(data, config, max_ips=100)
        assert len(result["data"]) == 0

    def test_max_ips_respected(self, parser, config):
        iocs = [{"ioc": f"1.2.3.{i}:80", "ioc_type": "ip:port"} for i in range(1, 20)]
        data = {"query_status": "ok", "data": iocs}
        result = parser._parse_threatfox_data(data, config, max_ips=3)
        assert len(result["data"]) == 3
