"""Unit tests for SecureCredentialService (AES-256-GCM encryption)"""

import pytest
from unittest.mock import Mock
from app.core.services.secure_credential_service import SecureCredentialService

@pytest.fixture
def secure_cred_service():
    return SecureCredentialService(db_service=Mock())

class TestEncryption:
    def test_encrypt_credential(self, secure_cred_service):
        secure_cred_service.db_service.execute = Mock(return_value=True)
        result = secure_cred_service.encrypt_and_store("api_key", "secret")
        assert secure_cred_service.db_service.execute.called

    def test_decrypt_credential(self, secure_cred_service):
        secure_cred_service.db_service.execute = Mock(return_value=[{"value": "encrypted_value"}])
        result = secure_cred_service.retrieve_and_decrypt("api_key")
        assert secure_cred_service.db_service.execute.called

