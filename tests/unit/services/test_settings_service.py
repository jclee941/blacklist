"""
Unit tests for SettingsService

Tests cover:
- System settings persistence
- Key-value storage
- Configuration retrieval
"""

import pytest
from unittest.mock import Mock
from app.core.services.settings_service import SettingsService


@pytest.fixture
def mock_db_service():
    return Mock()


@pytest.fixture
def settings_service(mock_db_service):
    return SettingsService(db_service=mock_db_service)


class TestSettingsCRUD:
    """Test settings CRUD operations"""

    def test_set_setting(self, settings_service):
        """Test setting a configuration value"""
        settings_service.db_service.execute = Mock(return_value=True)
        
        result = settings_service.set("feature_flag_x", "enabled")
        
        assert settings_service.db_service.execute.called

    def test_get_setting(self, settings_service):
        """Test getting a setting value"""
        settings_service.db_service.execute = Mock(return_value=[{"value": "enabled"}])
        
        result = settings_service.get("feature_flag_x")
        
        assert settings_service.db_service.execute.called

