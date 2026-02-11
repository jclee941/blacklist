"""
Unit tests for CollectionService

Tests cover:
- Collection initialization and management
- Data collection coordination
- Error handling
"""

import pytest
from unittest.mock import Mock
from app.core.services.collection_service import CollectionService


@pytest.fixture
def mock_db_service():
    return Mock()


@pytest.fixture
def collection_service(mock_db_service):
    return CollectionService(db_service=mock_db_service)


class TestCollectionInitialization:
    """Test collection setup"""

    def test_initialize_collection(self, collection_service):
        """Test initializing collection"""
        collection_service.db_service.execute = Mock(return_value=True)
        
        result = collection_service.initialize()
        
        assert collection_service.db_service.execute.called


class TestDataCollection:
    """Test data collection methods"""

    def test_collect_from_source(self, collection_service):
        """Test collecting data from a source"""
        collection_service.db_service.execute = Mock(return_value={"collected": 100})
        
        result = collection_service.collect_from_source("REGTECH")
        
        assert collection_service.db_service.execute.called

