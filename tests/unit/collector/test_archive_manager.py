"""Tests for collector/core/archive_manager.py — file archiving."""

import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestGenerateArchiveFilename:
    def test_basic_filename(self):
        from core.archive_manager import generate_archive_filename

        name = generate_archive_filename("secudium", "blacklist.xls")
        assert name.startswith("SECUDIUM_")
        assert name.endswith("_blacklist.xls")

    def test_with_period(self):
        from core.archive_manager import generate_archive_filename

        name = generate_archive_filename("REGTECH", "page1.html", "2026-02-01", "2026-02-11")
        assert "P20260201-20260211" in name

    def test_without_period(self):
        from core.archive_manager import generate_archive_filename

        name = generate_archive_filename("REGTECH", "page1.html")
        assert "P" not in name.split("_", 2)[2] or name.count("_") == 2


class TestNormalizeDate:
    def test_hyphenated(self):
        from core.archive_manager import _normalize_date

        assert _normalize_date("2026-02-01") == "20260201"

    def test_dotted(self):
        from core.archive_manager import _normalize_date

        assert _normalize_date("2026.02.01") == "20260201"

    def test_slashed(self):
        from core.archive_manager import _normalize_date

        assert _normalize_date("2026/02/01") == "20260201"

    def test_already_compact(self):
        from core.archive_manager import _normalize_date

        assert _normalize_date("20260201") == "20260201"

    def test_non_standard_passthrough(self):
        from core.archive_manager import _normalize_date

        assert _normalize_date("Feb 2026") == "Feb 2026"


class TestArchiveFile:
    @patch("core.archive_manager.CollectorConfig")
    def test_archive_disabled_returns_none(self, mock_config, tmp_path):
        from core.archive_manager import archive_file

        mock_config.ARCHIVE_ENABLED = False
        result = archive_file("SECUDIUM", str(tmp_path / "test.txt"))
        assert result is None

    @patch("core.archive_manager.CollectorConfig")
    def test_source_not_found_returns_none(self, mock_config):
        from core.archive_manager import archive_file

        mock_config.ARCHIVE_ENABLED = True
        result = archive_file("SECUDIUM", "/nonexistent/path/file.xls")
        assert result is None

    @patch("core.archive_manager.CollectorConfig")
    def test_archive_success(self, mock_config, tmp_path):
        from core.archive_manager import archive_file

        mock_config.ARCHIVE_ENABLED = True
        mock_config.ARCHIVE_DIR = str(tmp_path / "archive")

        src = tmp_path / "original.xls"
        src.write_text("data")

        result = archive_file("SECUDIUM", str(src))

        assert result is not None
        assert os.path.exists(result)


class TestArchiveContent:
    @patch("core.archive_manager.CollectorConfig")
    def test_archive_disabled_returns_none(self, mock_config):
        from core.archive_manager import archive_content

        mock_config.ARCHIVE_ENABLED = False
        result = archive_content("REGTECH", "<html>data</html>", "page1.html")
        assert result is None

    @patch("core.archive_manager.CollectorConfig")
    def test_archive_content_success(self, mock_config, tmp_path):
        from core.archive_manager import archive_content

        mock_config.ARCHIVE_ENABLED = True
        mock_config.ARCHIVE_DIR = str(tmp_path / "archive")

        result = archive_content("REGTECH", "<html>test</html>", "page1.html", "2026-01-01", "2026-01-31")

        assert result is not None
        assert os.path.exists(result)
        with open(result, "r") as f:
            assert f.read() == "<html>test</html>"
