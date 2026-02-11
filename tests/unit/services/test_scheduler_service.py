"""Unit tests for CollectionScheduler"""

import pytest
from unittest.mock import Mock
from app.core.services.scheduler_service import CollectionScheduler

@pytest.fixture
def scheduler_service():
    return CollectionScheduler(db_service=Mock())

class TestScheduler:
    def test_schedule_collection(self, scheduler_service):
        scheduler_service.db_service.execute = Mock(return_value=True)
        result = scheduler_service.schedule_collection("REGTECH", "0 */6 * * *")
        assert scheduler_service.db_service.execute.called

    def test_list_scheduled_jobs(self, scheduler_service):
        scheduler_service.db_service.execute = Mock(return_value=[{"source": "REGTECH"}])
        result = scheduler_service.list_scheduled_jobs()
        assert scheduler_service.db_service.execute.called

