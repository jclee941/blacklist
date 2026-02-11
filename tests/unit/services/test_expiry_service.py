"""
Unit tests for IPExpiryService

Tests cover:
- IP expiration detection
- Deactivation of expired IPs
- Batch operations
"""

import pytest
from unittest.mock import Mock
from app.core.services.expiry_service import IPExpiryService


@pytest.fixture
def mock_db_service():
    return Mock()


@pytest.fixture
def expiry_service(mock_db_service):
    return IPExpiryService(db_service=mock_db_service)


class TestExpiryDetection:
    """Test IP expiration detection"""

    def test_find_expired_ips(self, expiry_service):
        """Test finding expired IPs"""
        expiry_service.db_service.execute = Mock(return_value=[
            {"ip": "1.2.3.4"}
        ])
        
        result = expiry_service.find_expired_ips(days=30)
        
        assert expiry_service.db_service.execute.called

    def test_deactivate_expired_ips(self, expiry_service):
        """Test deactivating expired IPs"""
        expiry_service.db_service.execute = Mock(return_value=True)
        
        result = expiry_service.deactivate_expired_ips(days=30)
        
        assert expiry_service.db_service.execute.called

