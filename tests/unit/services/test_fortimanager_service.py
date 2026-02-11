"""Unit tests for FortiManagerPushService"""

import pytest
from unittest.mock import Mock
from app.core.services.fortimanager_push_service import FortiManagerPushService

@pytest.fixture
def fortimanager_service():
    return FortiManagerPushService(db_service=Mock())

class TestFortiManagerPush:
    def test_push_blacklist(self, fortimanager_service):
        fortimanager_service.db_service.execute = Mock(return_value=[{"ip": "1.2.3.4"}])
        result = fortimanager_service.push_blacklist()
        assert fortimanager_service.db_service.execute.called

    def test_sync_status(self, fortimanager_service):
        result = fortimanager_service.get_sync_status()
        assert result is not None

