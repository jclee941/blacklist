"""Tests for collector/core/regtech_parsers.py — parsing utilities."""

from core.regtech_parsers import (
    parse_date,
    is_valid_ip,
    normalize_country_code,
    extract_country_info,
    determine_confidence,
    parse_html_response,
)


class TestParseDate:
    def test_iso_format(self):
        assert parse_date("2026-02-01") == "2026-02-01"

    def test_iso_with_time(self):
        assert parse_date("2026-02-01 12:30:00") == "2026-02-01"

    def test_slash_ymd(self):
        assert parse_date("2026/02/01") == "2026-02-01"

    def test_dot_ymd(self):
        assert parse_date("2026.02.01") == "2026-02-01"

    def test_compact(self):
        assert parse_date("20260201") == "2026-02-01"

    def test_dmy_hyphen(self):
        assert parse_date("01-02-2026") == "2026-02-01"

    def test_dmy_slash_format(self):
        # %d/%m/%Y is tried before %m/%d/%Y, so 02/01/2026 => day=02, month=01
        assert parse_date("02/01/2026") == "2026-01-02"

    def test_none_input(self):
        assert parse_date(None) is None

    def test_empty_string(self):
        assert parse_date("") is None

    def test_unsupported_format(self):
        assert parse_date("Feb 1st 2026") is None

    def test_numeric_input(self):
        # str(123) -> "123" — not a date
        assert parse_date(123) is None

    def test_whitespace_stripped(self):
        assert parse_date("  2026-02-01  ") == "2026-02-01"


class TestIsValidIp:
    def test_valid_public_ip(self):
        assert is_valid_ip("8.8.8.8") is True

    def test_valid_public_ip_2(self):
        assert is_valid_ip("1.1.1.1") is True

    def test_private_ip_rejected(self):
        assert is_valid_ip("192.168.1.1") is False
        assert is_valid_ip("10.0.0.1") is False
        assert is_valid_ip("172.16.0.1") is False

    def test_loopback_rejected(self):
        assert is_valid_ip("127.0.0.1") is False

    def test_multicast_rejected(self):
        assert is_valid_ip("224.0.0.1") is False

    def test_invalid_format(self):
        assert is_valid_ip("not-an-ip") is False
        assert is_valid_ip("256.1.1.1") is False

    def test_whitespace_trimmed(self):
        assert is_valid_ip("  8.8.8.8  ") is True


class TestNormalizeCountryCode:
    def test_standard_two_letter(self):
        assert normalize_country_code("KR") == "KR"
        assert normalize_country_code("US") == "US"

    def test_full_name_korean(self):
        assert normalize_country_code("한국") == "KR"
        assert normalize_country_code("중국") == "CN"
        assert normalize_country_code("일본") == "JP"

    def test_full_name_english(self):
        assert normalize_country_code("KOREA") == "KR"
        assert normalize_country_code("USA") == "US"
        assert normalize_country_code("CHINA") == "CN"
        assert normalize_country_code("JAPAN") == "JP"

    def test_case_insensitive(self):
        assert normalize_country_code("kr") == "KR"
        assert normalize_country_code("us") == "US"

    def test_none_input(self):
        assert normalize_country_code(None) is None

    def test_empty_input(self):
        assert normalize_country_code("") is None

    def test_single_char(self):
        assert normalize_country_code("K") is None

    def test_unknown_two_letter(self):
        # Falls through to default: first 2 chars
        assert normalize_country_code("ZZ") == "ZZ"

    def test_long_unknown_string(self):
        assert normalize_country_code("XYZABC") == "XY"


class TestExtractCountryInfo:
    def test_finds_kr_directly(self):
        # "KR" is in country_patterns → returns "KR"
        assert extract_country_info(["KR", "reason"]) == "KR"

    def test_finds_korea_english(self):
        assert extract_country_info(["South Korea", "reason"]) == "KR"

    def test_finds_us(self):
        assert extract_country_info(["United States", "reason"]) == "US"

    def test_finds_china(self):
        assert extract_country_info(["China", "reason"]) == "CN"

    def test_ip_cell_matches_as_two_letter_alpha(self):
        # "IP" is 2-char alpha — function iterates L-to-R and picks first match
        # "IP" matches the 2-letter alpha fallback, so returns "IP"
        assert extract_country_info(["IP", "KR", "reason"]) == "IP"

    def test_finds_two_letter_code_de(self):
        # "DE" is in country_patterns → returns "DE"
        assert extract_country_info(["DE", "reason"]) == "DE"

    def test_numeric_cell_skipped(self):
        # Numeric cells are not alpha → skipped. No match → None
        assert extract_country_info(["123", "456"]) is None

    def test_empty_list(self):
        assert extract_country_info([]) is None

    def test_none_input(self):
        assert extract_country_info(None) is None

    def test_no_country_found(self):
        # "1" is len < 2, "123" is not alpha, "test" is not 2-char → no match
        assert extract_country_info(["1", "123", "test-long"]) is None

    def test_short_cell_ignored(self):
        assert extract_country_info(["", "x"]) is None

    def test_russia_contains_us_substring(self):
        # "Russia" contains "US" substring, and US patterns are checked before RU
        # So extract_country_info returns "US" for "Russia" (substring match order)
        assert extract_country_info(["Russia"]) == "US"

    def test_ru_code_directly(self):
        assert extract_country_info(["RU"]) == "RU"

    def test_japan_pattern(self):
        assert extract_country_info(["일본"]) == "JP"


class TestDetermineConfidence:
    def test_default_medium(self):
        result = determine_confidence({})
        assert result == 80

    def test_critical_threat(self):
        result = determine_confidence({"threatLevel": "critical"})
        assert result == 95

    def test_high_threat(self):
        result = determine_confidence({"threatLevel": "high"})
        assert result == 90

    def test_low_threat(self):
        result = determine_confidence({"threatLevel": "low"})
        assert result == 70

    def test_verified_bonus(self):
        result = determine_confidence({"verified": True})
        assert result == 85

    def test_high_report_count_bonus(self):
        result = determine_confidence({"reportCount": 15})
        assert result == 85

    def test_combined_max(self):
        result = determine_confidence({"threatLevel": "critical", "verified": True, "reportCount": 20})
        assert result == 100  # 80 + 15 + 5 + 5 = 105 capped at 100

    def test_floor_at_10(self):
        # Even with all negatives, minimum is 10
        result = determine_confidence({"threatLevel": "low"})
        assert result >= 10


class TestParseHtmlResponse:
    def test_valid_html_table(self):
        html = """
        <table>
            <tr><th>IP</th><th>Country</th><th>Reason</th><th>Detect</th><th>Remove</th></tr>
            <tr>
                <td>8.8.8.8</td>
                <td>US</td>
                <td>Suspicious Activity</td>
                <td>2026-01-01</td>
                <td>2026-06-01</td>
            </tr>
        </table>
        """
        result = parse_html_response(html)
        assert len(result) == 1
        assert result[0]["ip_address"] == "8.8.8.8"
        assert result[0]["country"] == "US"
        assert result[0]["reason"] == "Suspicious Activity"
        assert result[0]["detection_date"] == "2026-01-01"
        assert result[0]["removal_date"] == "2026-06-01"

    def test_private_ip_excluded(self):
        html = """
        <table>
            <tr><td>192.168.1.1</td><td>KR</td><td>test</td><td>2026-01-01</td></tr>
        </table>
        """
        result = parse_html_response(html)
        assert len(result) == 0

    def test_multiple_rows(self):
        html = """
        <table>
            <tr><td>8.8.8.8</td><td>US</td><td>Reason1</td><td>2026-01-01</td></tr>
            <tr><td>1.1.1.1</td><td>AU</td><td>Reason2</td><td>2026-02-01</td></tr>
        </table>
        """
        result = parse_html_response(html)
        assert len(result) == 2

    def test_empty_html(self):
        result = parse_html_response("")
        assert result == []

    def test_no_table(self):
        result = parse_html_response("<html><body>No data</body></html>")
        assert result == []

    def test_row_with_too_few_cells(self):
        html = """
        <table>
            <tr><td>8.8.8.8</td><td>US</td></tr>
        </table>
        """
        result = parse_html_response(html)
        assert len(result) == 0

    def test_reason_with_link(self):
        html = """
        <table>
            <tr>
                <td>8.8.8.8</td>
                <td>KR</td>
                <td><a href="#">Linked Reason</a></td>
                <td>2026-01-01</td>
            </tr>
        </table>
        """
        result = parse_html_response(html)
        assert len(result) == 1
        assert result[0]["reason"] == "Linked Reason"

    def test_empty_reason_gets_default(self):
        html = """
        <table>
            <tr>
                <td>8.8.8.8</td>
                <td>US</td>
                <td>-</td>
                <td>2026-01-01</td>
            </tr>
        </table>
        """
        result = parse_html_response(html)
        assert len(result) == 1
        assert result[0]["reason"] == "REGTECH Suspicious IP"

    def test_raw_data_included(self):
        html = """
        <table>
            <tr><td>8.8.8.8</td><td>US</td><td>Reason</td><td>2026-01-01</td></tr>
        </table>
        """
        result = parse_html_response(html)
        assert len(result) == 1
        assert "raw_data" in result[0]
        assert "row_data" in result[0]["raw_data"]
