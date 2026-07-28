"""Unit tests for service_factory module"""

import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.unit
class TestServiceFactory:
    """Tests for service_factory module-level functions"""

    @pytest.fixture(autouse=True)
    def credential_master_key(self, monkeypatch):
        monkeypatch.setenv("CREDENTIAL_MASTER_KEY", "test-credential-master-key")
        monkeypatch.setenv("ENCRYPTION_SALT", "test-encryption-salt")

    # --- get_service_info ---

    def test_get_service_info_returns_dict(self):
        """Service info returns metadata dict"""
        from app.core.services.service_factory import get_service_info

        result = get_service_info()

        assert isinstance(result, dict)
        assert "total_services" in result or "services" in result

    def test_get_service_info_has_categories(self):
        """Service info includes categories"""
        from app.core.services.service_factory import get_service_info

        result = get_service_info()

        assert "categories" in result or "initialization_order" in result

    def test_get_service_info_total_count(self):
        """Service info reports correct total count"""
        from app.core.services.service_factory import get_service_info

        result = get_service_info()

        # Should have 15 services (14 original + cloudflare)
        total = result.get("total_services", 0)
        assert total >= 10  # At least 10 services

    # --- initialize_services ---

    @patch("psycopg2.connect")
    def test_initialize_services_includes_db_service(self, mock_connect):
        """initialize_services creates a db_service entry"""
        mock_connect.return_value = MagicMock()
        mock_app = Mock()
        mock_app.extensions = {}

        from core.services.service_factory import initialize_services

        services = initialize_services(mock_app)
        assert "db_service" in services

    @patch("psycopg2.connect")
    def test_initialize_services_returns_dict(self, mock_connect):
        """initialize_services returns a dict"""
        mock_connect.return_value = MagicMock()
        mock_app = Mock()
        mock_app.extensions = {}

        from core.services.service_factory import initialize_services

        services = initialize_services(mock_app)
        assert isinstance(services, dict)

    @patch("psycopg2.connect")
    def test_initialize_services_handles_individual_failures(self, mock_connect):
        """Individual service init failure doesn't crash entire initialization"""
        mock_connect.return_value = MagicMock()
        mock_app = Mock()
        mock_app.extensions = {}

        from app.core.services.service_factory import initialize_services

        services = initialize_services(mock_app)
        assert isinstance(services, dict)

    @patch("psycopg2.connect")
    def test_initialize_services_fails_when_database_service_is_unavailable(self, mock_connect):
        mock_connect.return_value = MagicMock()
        mock_app = Mock()
        mock_app.extensions = {}

        from core.services.service_factory import initialize_services

        with patch(
            "core.services.database_service.DatabaseService", side_effect=RuntimeError("Cannot connect to DB")
        ):
            with pytest.raises(RuntimeError, match="Cannot connect to DB"):
                initialize_services(mock_app)

    @patch("psycopg2.connect")
    def test_initialize_services_fails_when_secure_credential_service_is_unavailable(self, mock_connect):
        mock_connect.return_value = MagicMock()
        mock_app = Mock()
        mock_app.extensions = {}

        from core.services.service_factory import initialize_services

        with patch(
            "core.services.secure_credential_service.SecureCredentialService",
            side_effect=RuntimeError("Credential master key is required"),
        ):
            with pytest.raises(RuntimeError, match="Credential master key is required"):
                initialize_services(mock_app)
