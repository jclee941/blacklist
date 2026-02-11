"""Unit tests for ABTestService"""

import pytest
from unittest.mock import Mock
from app.core.services.ab_test_service import ABTestService

@pytest.fixture
def ab_test_service():
    return ABTestService()

class TestABTest:
    def test_create_test(self, ab_test_service):
        result = ab_test_service.create_test("feature_x", [0.5, 0.5])
        assert result is not None

    def test_get_variant(self, ab_test_service):
        result = ab_test_service.get_variant("user_123", "feature_x")
        assert result in [0, 1]

