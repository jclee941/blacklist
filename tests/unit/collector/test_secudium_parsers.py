import pytest
import pandas as pd
from unittest.mock import patch
from core.secudium_parsers import (
    parse_black_ip_list,
    extract_download_info,
    parse_xls_file,
    _is_valid_ip_or_cidr,
    _extract_reason,
)


@pytest.mark.unit
class TestParseBlackIpList:
    def test_valid_response(self):
        response = {
            "rows": [
                {
                    "id": 20176,
                    "data": [
                        "",
                        "",
                        "[SK쉴더스] 신규 침해 Black IP - 2026-02-06",
                        "정예린",
                        "2026-02-06 01:25:51",
                        '<button onclick=\'download("abc-uuid", "file.xls");\'>Down</button>',
                        "0",
                        "N",
                    ],
                    "userData": {"edit_yn": "N"},
                }
            ]
        }
        result = parse_black_ip_list(response)
        assert len(result) == 1
        assert result[0]["id"] == 20176
        assert result[0]["title"] == "[SK쉴더스] 신규 침해 Black IP - 2026-02-06"
        assert result[0]["author"] == "정예린"
        assert result[0]["date"] == "2026-02-06 01:25:51"
        assert "download" in result[0]["download_html"]
        assert result[0]["count"] == "0"
        assert result[0]["edit_yn"] == "N"

    def test_empty_rows(self):
        assert parse_black_ip_list({"rows": []}) == []

    def test_missing_rows_key(self):
        assert parse_black_ip_list({}) == []

    def test_none_input(self):
        assert parse_black_ip_list(None) == []

    def test_row_with_short_data_skipped(self):
        response = {
            "rows": [
                {"id": 1, "data": ["a", "b"]},
                {
                    "id": 2,
                    "data": ["", "", "Title", "Author", "2026-01-01", "<btn>", "1", "Y"],
                },
            ]
        }
        result = parse_black_ip_list(response)
        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_multiple_rows(self):
        rows = []
        for i in range(5):
            rows.append(
                {
                    "id": i,
                    "data": ["", "", f"Title {i}", "Author", "2026-01-01", "<btn>", "0", "N"],
                }
            )
        result = parse_black_ip_list({"rows": rows})
        assert len(result) == 5
        assert [r["id"] for r in result] == [0, 1, 2, 3, 4]


@pytest.mark.unit
class TestExtractDownloadInfo:
    def test_standard_download_button(self):
        html = """<button onclick='download("abc-def-123", "blackip_20260206.xls");'>Down</button>"""
        result = extract_download_info(html)
        assert result is not None
        server_filename, display_filename = result
        assert server_filename == "abc-def-123"
        assert display_filename == "blackip_20260206.xls"

    def test_double_quoted_onclick(self):
        html = "<button onclick=\"download('uuid-456', 'report.xls');\">Download</button>"
        result = extract_download_info(html)
        assert result is not None
        server_filename, _ = result
        assert server_filename == "uuid-456"

    def test_url_encoded_filename(self):
        html = """<button onclick='download("uuid", "%ED%85%8C%EC%8A%A4%ED%8A%B8.xls");'>Down</button>"""
        result = extract_download_info(html)
        assert result is not None
        _, display_filename = result
        assert display_filename == "테스트.xls"

    def test_empty_string(self):
        assert extract_download_info("") is None

    def test_no_download_function(self):
        assert extract_download_info("<button>Click</button>") is None

    def test_none_input(self):
        assert extract_download_info(None) is None

    def test_malformed_html(self):
        assert extract_download_info("download(broken") is None


@pytest.mark.unit
class TestIsValidIpOrCidr:
    def test_valid_ipv4(self):
        assert _is_valid_ip_or_cidr("192.168.1.1") is True
        assert _is_valid_ip_or_cidr("10.0.0.1") is True
        assert _is_valid_ip_or_cidr("8.8.8.8") is True

    def test_valid_cidr(self):
        assert _is_valid_ip_or_cidr("192.168.1.0/24") is True
        assert _is_valid_ip_or_cidr("10.0.0.0/8") is True

    def test_invalid_values(self):
        assert _is_valid_ip_or_cidr("") is False
        assert _is_valid_ip_or_cidr("not-an-ip") is False
        assert _is_valid_ip_or_cidr("256.1.1.1") is False
        assert _is_valid_ip_or_cidr("1.2.3") is False

    def test_loopback_and_special(self):
        assert _is_valid_ip_or_cidr("127.0.0.1") is True
        assert _is_valid_ip_or_cidr("0.0.0.0") is True

    def test_cidr_with_invalid_mask(self):
        assert _is_valid_ip_or_cidr("10.0.0.0/33") is False


@pytest.mark.unit
class TestParseXlsFile:
    @patch("core.secudium_parsers._parse_xls_with_pandas")
    def test_pandas_success(self, mock_pandas):
        mock_pandas.return_value = [
            {"ip": "1.2.3.4", "port": 80, "description": "Malware C2", "source_date": "2026-01-01"}
        ]
        result = parse_xls_file("/fake/path.xls")
        assert len(result) == 1
        assert result[0]["ip"] == "1.2.3.4"
        mock_pandas.assert_called_once_with("/fake/path.xls")

    @patch("core.secudium_parsers._parse_xls_as_text")
    @patch("core.secudium_parsers._parse_xls_with_pandas")
    def test_fallback_to_text_on_pandas_error(self, mock_pandas, mock_text):
        mock_pandas.side_effect = Exception("pandas failed")
        mock_text.return_value = [{"ip": "5.6.7.8", "port": None, "description": "", "source_date": None}]

        result = parse_xls_file("/fake/path.xls")
        assert len(result) == 1
        assert result[0]["ip"] == "5.6.7.8"
        mock_text.assert_called_once()

    @patch("core.secudium_parsers._parse_xls_with_pandas")
    def test_empty_result(self, mock_pandas):
        mock_pandas.return_value = []
        result = parse_xls_file("/fake/path.xls")
        assert result == []

    def test_nonexistent_file(self):
        result = parse_xls_file("/nonexistent/file.xls")
        assert result == []


@pytest.mark.unit
class TestExtractReason:
    def test_korean_detect_reason_column_returns_value(self):
        columns = pd.Index(["IP", "탐지사유"])
        row = pd.Series({"IP": "1.2.3.4", "탐지사유": "악성 트래픽 탐지"})

        result = _extract_reason(row, columns)

        assert result == "악성 트래픽 탐지"

    def test_reason_column_case_insensitive_returns_value(self):
        columns = pd.Index(["Reason", "IP"])
        row = pd.Series({"Reason": "C2 Activity", "IP": "5.6.7.8"})

        result = _extract_reason(row, columns)

        assert result == "C2 Activity"

    def test_threat_column_with_nan_string_returns_empty(self):
        columns = pd.Index(["위협", "IP"])
        row = pd.Series({"위협": "nan", "IP": "8.8.8.8"})

        result = _extract_reason(row, columns)

        assert result == ""

    def test_no_matching_column_returns_empty(self):
        columns = pd.Index(["description", "category"])
        row = pd.Series({"description": "test", "category": "malware"})

        result = _extract_reason(row, columns)

        assert result == ""

    def test_multiple_matching_columns_returns_first_match(self):
        columns = pd.Index(["차단사유", "reason", "위협"])
        row = pd.Series({"차단사유": "첫 번째", "reason": "두 번째", "위협": "세 번째"})

        result = _extract_reason(row, columns)

        assert result == "첫 번째"

    def test_empty_string_value_returns_empty(self):
        columns = pd.Index(["block_reason", "IP"])
        row = pd.Series({"block_reason": "", "IP": "9.9.9.9"})

        result = _extract_reason(row, columns)

        assert result == ""
