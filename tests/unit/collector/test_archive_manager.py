"""Tests for collector/core/archive_manager.py — file archiving."""

import os
from unittest.mock import patch


class TestGenerateArchiveFilename:
    def test_basic_filename(self):
        from collector.core.archive_manager import generate_archive_filename

        name = generate_archive_filename("regtech", "page1.html")
        assert name.startswith("REGTECH_")
        assert name.endswith("_page1.html")

    def test_with_period(self):
        from collector.core.archive_manager import generate_archive_filename

        name = generate_archive_filename("REGTECH", "page1.html", "2026-02-01", "2026-02-11")
        assert "P20260201-20260211" in name

    def test_without_period(self):
        from collector.core.archive_manager import generate_archive_filename

        name = generate_archive_filename("REGTECH", "page1.html")
        assert "P" not in name.split("_", 2)[2] or name.count("_") == 2

    def test_path_components_cannot_escape_archive_root(self):
        from collector.core.archive_manager import generate_archive_filename

        name = generate_archive_filename("../outside", "../../payload.html")

        assert "/" not in name
        assert "\\" not in name
        assert ".." not in name


class TestNormalizeDate:
    def test_hyphenated(self):
        from collector.core.archive_manager import _normalize_date

        assert _normalize_date("2026-02-01") == "20260201"

    def test_dotted(self):
        from collector.core.archive_manager import _normalize_date

        assert _normalize_date("2026.02.01") == "20260201"

    def test_slashed(self):
        from collector.core.archive_manager import _normalize_date

        assert _normalize_date("2026/02/01") == "20260201"

    def test_already_compact(self):
        from collector.core.archive_manager import _normalize_date

        assert _normalize_date("20260201") == "20260201"

    def test_non_standard_date_is_filename_safe(self):
        from collector.core.archive_manager import _normalize_date

        assert _normalize_date("Feb 2026") == "Feb_2026"


class TestArchiveFile:
    @patch("collector.core.archive_manager.CollectorConfig")
    def test_archive_disabled_returns_none(self, mock_config, tmp_path):
        from collector.core.archive_manager import archive_file

        mock_config.ARCHIVE_ENABLED = False
        result = archive_file("REGTECH", str(tmp_path / "test.txt"))
        assert result is None

    @patch("collector.core.archive_manager.CollectorConfig")
    def test_source_not_found_returns_none(self, mock_config):
        from collector.core.archive_manager import archive_file

        mock_config.ARCHIVE_ENABLED = True
        result = archive_file("REGTECH", "/nonexistent/path/file.html")
        assert result is None

    @patch("collector.core.archive_manager.CollectorConfig")
    def test_archive_success(self, mock_config, tmp_path):
        from collector.core.archive_manager import archive_file

        mock_config.ARCHIVE_ENABLED = True
        mock_config.ARCHIVE_DIR = str(tmp_path / "archive")
        mock_config.MAX_ARCHIVE_BYTES = 1024
        mock_config.ARCHIVE_RETENTION_DAYS = 30

        src = tmp_path / "original.html"
        src.write_text("data")

        result = archive_file("REGTECH", str(src))

        assert result is not None
        assert os.path.exists(result)


class TestArchiveContent:
    @patch("collector.core.archive_manager.CollectorConfig")
    def test_archive_disabled_returns_none(self, mock_config):
        from collector.core.archive_manager import archive_content

        mock_config.ARCHIVE_ENABLED = False
        result = archive_content("REGTECH", "<html>data</html>", "page1.html")
        assert result is None

    @patch("collector.core.archive_manager.CollectorConfig")
    def test_archive_content_success(self, mock_config, tmp_path):
        from collector.core.archive_manager import archive_content

        mock_config.ARCHIVE_ENABLED = True
        mock_config.ARCHIVE_DIR = str(tmp_path / "archive")
        mock_config.MAX_ARCHIVE_BYTES = 1024
        mock_config.ARCHIVE_RETENTION_DAYS = 30

        result = archive_content("REGTECH", "<html>test</html>", "page1.html", "2026-01-01", "2026-01-31")

        assert result is not None
        assert os.path.exists(result)
        with open(result, "r") as f:
            assert f.read() == "<html>test</html>"

    @patch("collector.core.archive_manager.CollectorConfig")
    def test_archive_content_rejects_write_beyond_capacity(self, mock_config, tmp_path):
        # Given: an archive with a ten-byte hard capacity.
        from collector.core.archive_manager import archive_content

        mock_config.ARCHIVE_ENABLED = True
        mock_config.ARCHIVE_DIR = str(tmp_path / "archive")
        mock_config.MAX_ARCHIVE_BYTES = 10
        mock_config.ARCHIVE_RETENTION_DAYS = 30

        # When: content larger than the configured capacity is archived.
        result = archive_content("REGTECH", "x" * 11, "page.html")

        # Then: no archive path is created.
        assert result is None
        assert not (tmp_path / "archive").exists()
