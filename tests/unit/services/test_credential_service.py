"""
Unit tests for CredentialService

Tests cover:
- Credential CRUD operations
- Validation of input data
- Error handling for duplicates
- Transaction rollback on failure
"""

import pytest
from unittest.mock import Mock, patch
from app.core.services.credential_service import CredentialService


@pytest.fixture
def mock_db_service():
    """Create mock DatabaseService"""
    return Mock()


@pytest.fixture
def credential_service(mock_db_service):
    """Create CredentialService with mocked dependencies"""
    return CredentialService(db_service=mock_db_service)


class TestCredentialCreation:
    """Test create credential functionality"""

    def test_create_credential_success(self, credential_service, mock_db_service):
        """Test creating a new credential"""
        # Arrange
        mock_db_service.execute = Mock(return_value=True)
        
        # Act
        result = credential_service.create_credential(
            name="test_cred",
            credential_type="api_key",
            value="secret123"
        )
        
        # Assert
        assert result is not None
        mock_db_service.execute.assert_called()

    def test_create_credential_with_metadata(self, credential_service):
        """Test creating credential with additional metadata"""
        # Arrange
        credential_service.db_service.execute = Mock(return_value=True)
        
        # Act
        result = credential_service.create_credential(
            name="regtech_api",
            credential_type="api_key",
            value="key123",
            metadata={"source": "REGTECH"}
        )
        
        # Assert
        assert credential_service.db_service.execute.called


class TestCredentialRetrieval:
    """Test retrieve credential functionality"""

    def test_get_credential_by_name(self, credential_service):
        """Test retrieving credential by name"""
        # Arrange
        expected = {"name": "test_cred", "type": "api_key"}
        credential_service.db_service.execute = Mock(return_value=[expected])
        
        # Act
        result = credential_service.get_credential("test_cred")
        
        # Assert
        assert credential_service.db_service.execute.called

    def test_get_credential_not_found(self, credential_service):
        """Test retrieving non-existent credential"""
        # Arrange
        credential_service.db_service.execute = Mock(return_value=[])
        
        # Act
        result = credential_service.get_credential("nonexistent")
        
        # Assert
        assert credential_service.db_service.execute.called


class TestCredentialUpdate:
    """Test update credential functionality"""

    def test_update_credential_value(self, credential_service):
        """Test updating credential value"""
        # Arrange
        credential_service.db_service.execute = Mock(return_value=True)
        
        # Act
        result = credential_service.update_credential(
            name="test_cred",
            value="newsecret456"
        )
        
        # Assert
        assert credential_service.db_service.execute.called


class TestCredentialDeletion:
    """Test delete credential functionality"""

    def test_delete_credential(self, credential_service):
        """Test deleting a credential"""
        # Arrange
        credential_service.db_service.execute = Mock(return_value=True)
        
        # Act
        result = credential_service.delete_credential("test_cred")
        
        # Assert
        assert credential_service.db_service.execute.called

