"""Tests for parse_excel_file from core/regtech_excel.py."""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pandas as pd

from core.regtech_excel import parse_excel_file, download_excel_data


class TestParseExcelFile:
    def _make_excel(self, columns, rows):
        df = pd.DataFrame(rows, columns=columns)
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        df.to_excel(tmp.name, index=False, engine="openpyxl")
        return tmp.name

    def test_basic_ip_column(self):
        path = self._make_excel(
            ["ip_address", "country", "reason"],
            [["8.8.8.8", "US", "Malware"]],
        )
        try:
            result = parse_excel_file(path)
            assert len(result) == 1
            assert result[0]["ip_address"] == "8.8.8.8"
            assert result[0]["source"] == "REGTECH"
        finally:
            os.unlink(path)

    def test_private_ip_excluded(self):
        path = self._make_excel(["ip"], [["192.168.1.1"], ["8.8.8.8"]])
        try:
            result = parse_excel_file(path)
            assert len(result) == 1
            assert result[0]["ip_address"] == "8.8.8.8"
        finally:
            os.unlink(path)

    def test_country_column_parsed(self):
        path = self._make_excel(
            ["ip_address", "국가"],
            [["8.8.8.8", "KR"]],
        )
        try:
            result = parse_excel_file(path)
            assert result[0]["country"] == "KR"
        finally:
            os.unlink(path)

    def test_reason_column_parsed(self):
        path = self._make_excel(
            ["ip_address", "사유"],
            [["8.8.8.8", "Botnet C2"]],
        )
        try:
            result = parse_excel_file(path)
            assert result[0]["reason"] == "Botnet C2"
        finally:
            os.unlink(path)

    def test_default_reason_when_no_reason_column(self):
        path = self._make_excel(["ip_address"], [["8.8.8.8"]])
        try:
            result = parse_excel_file(path)
            assert result[0]["reason"] == "REGTECH Excel Import"
        finally:
            os.unlink(path)

    def test_detection_date_column(self):
        path = self._make_excel(
            ["ip_address", "탐지일"],
            [["8.8.8.8", "2026-01-15"]],
        )
        try:
            result = parse_excel_file(path)
            assert result[0]["detection_date"] == "2026-01-15"
        finally:
            os.unlink(path)

    def test_removal_date_column(self):
        path = self._make_excel(
            ["ip_address", "해제일"],
            [["8.8.8.8", "2026-06-01"]],
        )
        try:
            result = parse_excel_file(path)
            assert result[0]["removal_date"] == "2026-06-01"
        finally:
            os.unlink(path)

    def test_fallback_first_column_as_ip(self):
        path = self._make_excel(["data"], [["8.8.8.8"]])
        try:
            result = parse_excel_file(path)
            assert len(result) == 1
            assert result[0]["ip_address"] == "8.8.8.8"
        finally:
            os.unlink(path)

    def test_addr_column_name_detected(self):
        path = self._make_excel(["src_addr"], [["8.8.8.8"]])
        try:
            result = parse_excel_file(path)
            assert len(result) == 1
        finally:
            os.unlink(path)

    def test_multiple_rows(self):
        path = self._make_excel(
            ["ip_address"],
            [["8.8.8.8"], ["1.1.1.1"], ["9.9.9.9"]],
        )
        try:
            result = parse_excel_file(path)
            assert len(result) == 3
        finally:
            os.unlink(path)

    def test_invalid_file_returns_empty(self):
        result = parse_excel_file("/nonexistent/path.xlsx")
        assert result == []

    def test_raw_data_has_excel_import_flag(self):
        path = self._make_excel(["ip_address"], [["8.8.8.8"]])
        try:
            result = parse_excel_file(path)
            assert result[0]["raw_data"] == {"excel_import": True}
        finally:
            os.unlink(path)

    def test_is_active_true(self):
        path = self._make_excel(["ip_address"], [["8.8.8.8"]])
        try:
            result = parse_excel_file(path)
            assert result[0]["is_active"] is True
        finally:
            os.unlink(path)


class TestDownloadExcelData:
    def test_rate_limiter_fails_returns_empty(self):
        session = MagicMock()
        rate_limiter = MagicMock()
        rate_limiter.wait_if_needed.return_value = False

        result = download_excel_data(session, rate_limiter, None, "https://example.com", "2026-01-01", "2026-03-31")
        assert result == []

    @patch("core.regtech_excel.subprocess.run")
    def test_curl_failure_returns_empty(self, mock_run):
        session = MagicMock()
        session.cookies = []
        rate_limiter = MagicMock()
        rate_limiter.wait_if_needed.return_value = True
        mock_run.return_value = MagicMock(returncode=1, stderr="connection refused")

        result = download_excel_data(session, rate_limiter, None, "https://example.com", "2026-01-01", "2026-03-31")
        assert result == []

    @patch("core.regtech_excel.os.path.exists", return_value=False)
    @patch("core.regtech_excel.subprocess.run")
    def test_file_not_created_returns_empty(self, mock_run, mock_exists):
        session = MagicMock()
        session.cookies = []
        rate_limiter = MagicMock()
        rate_limiter.wait_if_needed.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        result = download_excel_data(session, rate_limiter, None, "https://example.com", "2026-01-01", "2026-03-31")
        assert result == []
