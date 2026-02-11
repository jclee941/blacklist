"""Unit tests for OptimizedBlacklistService"""

import pytest
from unittest.mock import Mock
from app.core.services.optimized_blacklist_service import OptimizedBlacklistService

@pytest.fixture
def optimized_service():
    return OptimizedBlacklistService(db_service=Mock())

class TestOptimizedBlacklist:
    def test_bulk_check(self, optimized_service):
        optimized_service.db_service.execute = Mock(return_value=[{"ip": "1.2.3.4", "blocked": True}])
        result = optimized_service.bulk_check(["1.2.3.4", "10.0.0.1"])
        assert optimized_service.db_service.execute.called

    def test_performance_metrics(self, optimized_service):
        result = optimized_service.get_performance_metrics()
        assert result is not None

