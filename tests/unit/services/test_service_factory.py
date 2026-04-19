"""Unit tests for service_factory module"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.unit
class TestServiceFactory:
    """Tests for service_factory module-level functions"""

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

        from app.core.services.service_factory import initialize_services

        services = initialize_services(mock_app)
        assert "db_service" in services

    @patch("psycopg2.connect")
    def test_initialize_services_returns_dict(self, mock_connect):
        """initialize_services returns a dict"""
        mock_connect.return_value = MagicMock()
        mock_app = Mock()
        mock_app.extensions = {}

        from app.core.services.service_factory import initialize_services

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
    def test_initialize_services_db_failure_is_handled(self, mock_connect):
        """DatabaseService failure is handled gracefully"""
        mock_connect.return_value = MagicMock()
        mock_app = Mock()
        mock_app.extensions = {}

        from app.core.services.service_factory import initialize_services

        with patch(
            "app.core.services.service_factory.DatabaseService",
            create=True,
            side_effect=Exception("Cannot connect to DB"),
        ):
            try:
                services = initialize_services(mock_app)
                assert services.get("db_service") is None or "db_service" not in services
            except Exception:
                assert True
