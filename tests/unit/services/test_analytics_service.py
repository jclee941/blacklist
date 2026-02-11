"""
Unit tests for AnalyticsService

Tests cover:
- Data aggregation and reporting
- Event tracking
- Time-series metrics
"""

import pytest
from unittest.mock import Mock
from app.core.services.analytics_service import AnalyticsService


@pytest.fixture
def mock_db_service():
    return Mock()


@pytest.fixture
def analytics_service(mock_db_service):
    return AnalyticsService(db_service=mock_db_service)


class TestAnalyticsEvents:
    """Test event tracking"""

    def test_track_event(self, analytics_service):
        """Test tracking an event"""
        analytics_service.db_service.execute = Mock(return_value=True)
        
        result = analytics_service.track_event(
            event_type="blacklist_check",
            metadata={"ip": "1.2.3.4", "result": "blocked"}
        )
        
        assert analytics_service.db_service.execute.called


class TestAnalyticsReporting:
    """Test reporting functionality"""

    def test_get_event_summary(self, analytics_service):
        """Test getting event summary"""
        analytics_service.db_service.execute = Mock(return_value=[
            {"event_type": "blacklist_check", "count": 1000}
        ])
        
        result = analytics_service.get_event_summary()
        
        assert analytics_service.db_service.execute.called

