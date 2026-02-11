"""Unit tests for RegtechConfigService"""

import pytest
from unittest.mock import Mock
from app.core.services.regtech_config_service import RegtechConfigService

@pytest.fixture
def regtech_config_service():
    return RegtechConfigService()

class TestRegtechConfig:
    def test_get_config(self, regtech_config_service):
        result = regtech_config_service.get_config()
        assert result is not None

    def test_update_config(self, regtech_config_service):
        result = regtech_config_service.update_config({"enabled": True})
        assert result is not None

