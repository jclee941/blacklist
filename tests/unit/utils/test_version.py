"""Unit tests for core.utils.version."""

import os
from unittest.mock import patch


from core.utils.version import get_app_version


class TestGetAppVersion:
    """Tests for get_app_version function."""

    def test_returns_env_version_when_set(self):
        """APP_VERSION env var takes highest priority."""
        with patch.dict(os.environ, {"APP_VERSION": "1.2.3"}):
            result = get_app_version()
            assert result == "1.2.3"

    def test_returns_string(self):
        """Should always return a string."""
        result = get_app_version()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_default_version_fallback(self):
        """When no env var and no VERSION file, returns a default version string."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove APP_VERSION to test file/default fallback
            os.environ.pop("APP_VERSION", None)
            result = get_app_version()
            assert isinstance(result, str)
            assert len(result) > 0

    def test_env_takes_priority_over_file(self):
        """APP_VERSION env should override file-based version."""
        with patch.dict(os.environ, {"APP_VERSION": "9.9.9"}):
            result = get_app_version()
            assert result == "9.9.9"

    def test_returns_nonempty_string(self):
        """Version should never be empty."""
        result = get_app_version()
        assert len(result.strip()) > 0
