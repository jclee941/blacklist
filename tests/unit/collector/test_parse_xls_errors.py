"""
#45 — parse_xls_file 에러 핸들링 테스트

Tests error handling in parse_xls_file, _parse_xls_with_pandas,
and _parse_xls_as_text for various failure scenarios.
"""

import os
import tempfile

import pytest
from unittest.mock import patch, MagicMock

PARSER_MODULE = "core.secudium_parsers"


@pytest.mark.unit
class TestParseXlsFileErrors:
    """Tests for parse_xls_file error handling."""

    def test_nonexistent_file_returns_empty(self):
        """Nonexistent file should return empty list, not raise."""
        from core.secudium_parsers import parse_xls_file

        result = parse_xls_file("/nonexistent/path/file.xls")
        assert result == []

    def test_empty_file_returns_empty(self):
        """Empty file should return empty list."""
        from core.secudium_parsers import parse_xls_file

        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as f:
            f.write(b"")
            tmp_path = f.name
        try:
            result = parse_xls_file(tmp_path)
            assert result == []
        finally:
            os.unlink(tmp_path)

    def test_corrupt_file_returns_empty(self):
        """Corrupt/random binary file should return empty list."""
        from core.secudium_parsers import parse_xls_file

        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe\xfd" * 100)
            tmp_path = f.name
        try:
            result = parse_xls_file(tmp_path)
            assert isinstance(result, list)
        finally:
            os.unlink(tmp_path)

    def test_pandas_failure_falls_back_to_text(self):
        """When pandas parsing fails, should fall back to text extraction."""
        from core.secudium_parsers import parse_xls_file

        # Create a file with IP-like text content
        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False, mode="wb") as f:
            f.write(b"Some header data\n192.168.1.1\n10.0.0.1\nmore data\n")
            tmp_path = f.name
        try:
            with patch(f"{PARSER_MODULE}._parse_xls_with_pandas", side_effect=Exception("pandas failed")):
                result = parse_xls_file(tmp_path)
                assert isinstance(result, list)
                # Text fallback should extract IPs via regex
                ips = [r["ip"] for r in result]
                assert "192.168.1.1" in ips
                assert "10.0.0.1" in ips
        finally:
            os.unlink(tmp_path)

    def test_both_parsers_fail_returns_empty(self):
        """When both pandas and text parsing fail, should return empty list."""
        from core.secudium_parsers import parse_xls_file

        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as f:
            f.write(b"no ip data here at all")
            tmp_path = f.name
        try:
            with patch(f"{PARSER_MODULE}._parse_xls_with_pandas", side_effect=Exception("pandas failed")):
                result = parse_xls_file(tmp_path)
                assert isinstance(result, list)
        finally:
            os.unlink(tmp_path)

    def test_permission_denied_returns_empty(self):
        """Permission denied should return empty list, not raise."""
        from core.secudium_parsers import parse_xls_file

        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as f:
            f.write(b"some data")
            tmp_path = f.name
        try:
            os.chmod(tmp_path, 0o000)
            result = parse_xls_file(tmp_path)
            assert isinstance(result, list)
        finally:
            os.chmod(tmp_path, 0o644)
            os.unlink(tmp_path)


@pytest.mark.unit
class TestParseXlsWithPandasErrors:
    """Tests for _parse_xls_with_pandas error cases."""

    def test_no_ip_column_found(self):
        """DataFrame with no IP-like column should return empty."""
        from core.secudium_parsers import _parse_xls_with_pandas

        import pandas as pd

        df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
        with patch("pandas.read_excel", return_value=df):
            result = _parse_xls_with_pandas("/fake/path.xls")
            assert result == []

    def test_empty_dataframe(self):
        """Empty DataFrame should return empty list."""
        from core.secudium_parsers import _parse_xls_with_pandas

        import pandas as pd

        df = pd.DataFrame()
        with patch("pandas.read_excel", return_value=df):
            result = _parse_xls_with_pandas("/fake/path.xls")
            assert result == []

    def test_xlrd_not_installed(self):
        """Should raise when xlrd engine is not available."""
        from core.secudium_parsers import _parse_xls_with_pandas

        with patch("pandas.read_excel", side_effect=ImportError("No module named 'xlrd'")):
            with pytest.raises(ImportError):
                _parse_xls_with_pandas("/fake/path.xls")


@pytest.mark.unit
class TestParseXlsAsTextErrors:
    """Tests for _parse_xls_as_text error cases."""

    def test_no_ips_in_binary(self):
        """Binary file with no IP patterns returns empty list."""
        from core.secudium_parsers import _parse_xls_as_text

        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as f:
            f.write(b"hello world no ips here")
            tmp_path = f.name
        try:
            result = _parse_xls_as_text(tmp_path)
            assert result == []
        finally:
            os.unlink(tmp_path)

    def test_filters_loopback_and_special(self):
        """Should filter out 0.*, 127.*, 255.* addresses."""
        from core.secudium_parsers import _parse_xls_as_text

        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False, mode="wb") as f:
            f.write(b"127.0.0.1 0.0.0.0 255.255.255.255 192.168.1.100")
            tmp_path = f.name
        try:
            result = _parse_xls_as_text(tmp_path)
            ips = [r["ip"] for r in result]
            assert "127.0.0.1" not in ips
            assert "0.0.0.0" not in ips
            assert "255.255.255.255" not in ips
            assert "192.168.1.100" in ips
        finally:
            os.unlink(tmp_path)

    def test_extracts_valid_ips(self):
        """Should extract valid public IPs from binary content."""
        from core.secudium_parsers import _parse_xls_as_text

        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False, mode="wb") as f:
            f.write(b"data 10.20.30.40 more 172.16.0.1 end")
            tmp_path = f.name
        try:
            result = _parse_xls_as_text(tmp_path)
            ips = [r["ip"] for r in result]
            assert "10.20.30.40" in ips
            assert "172.16.0.1" in ips
        finally:
            os.unlink(tmp_path)

    def test_description_set_to_regex_extracted(self):
        """Text-extracted IPs should have description='regex_extracted'."""
        from core.secudium_parsers import _parse_xls_as_text

        with tempfile.NamedTemporaryFile(suffix=".xls", delete=False, mode="wb") as f:
            f.write(b"192.168.50.1")
            tmp_path = f.name
        try:
            result = _parse_xls_as_text(tmp_path)
            if result:
                assert result[0]["description"] == "regex_extracted"
        finally:
            os.unlink(tmp_path)
