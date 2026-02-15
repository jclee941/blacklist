from datetime import datetime
from unittest.mock import Mock

import pytest

from app.core.services.optimized_blacklist_service import OptimizedBlacklistService


def _build_service_with_cursor(cursor):
    conn = Mock()
    conn.cursor.return_value = cursor
    db_service = Mock()
    db_service.get_connection.return_value = conn
    service = OptimizedBlacklistService(db_service=db_service)
    return service, db_service, conn


@pytest.mark.unit
class TestOptimizedBlacklistService:
    def test_constructor_requires_db_service(self):
        with pytest.raises(ValueError, match="db_service is required"):
            OptimizedBlacklistService(None)

    def test_get_unified_statistics_success(self):
        now = datetime(2026, 1, 1, 10, 0, 0)
        cursor = Mock()
        cursor.fetchone.side_effect = [
            {
                "total_ips": 10,
                "active_ips": 8,
                "sources": 3,
                "countries": 2,
                "last_update": now,
                "first_update": now,
                "recent_additions": 4,
                "high_confidence": 5,
                "avg_confidence": 77.5,
            },
            {
                "collection_count": 7,
                "last_collection": now,
                "successful_collections": 6,
            },
        ]

        service, _, _ = _build_service_with_cursor(cursor)
        result = service.get_unified_statistics()

        assert result["success"] is True
        assert result["statistics"]["total_ips"] == 10
        assert result["statistics"]["active_ips"] == 8
        assert result["statistics"]["last_update"] == now.isoformat()
        assert result["statistics"]["collection_count"] == 7

    def test_get_unified_statistics_not_stale_between_calls(self):
        cursor = Mock()
        first_time = datetime(2026, 1, 1, 10, 0, 0)
        second_time = datetime(2026, 1, 2, 10, 0, 0)
        cursor.fetchone.side_effect = [
            {
                "total_ips": 1,
                "active_ips": 1,
                "sources": 1,
                "countries": 1,
                "last_update": first_time,
                "first_update": first_time,
                "recent_additions": 1,
                "high_confidence": 1,
                "avg_confidence": 1,
            },
            {"collection_count": 1, "last_collection": first_time, "successful_collections": 1},
            {
                "total_ips": 2,
                "active_ips": 2,
                "sources": 1,
                "countries": 1,
                "last_update": second_time,
                "first_update": first_time,
                "recent_additions": 2,
                "high_confidence": 2,
                "avg_confidence": 2,
            },
            {"collection_count": 2, "last_collection": second_time, "successful_collections": 2},
        ]

        service, _, _ = _build_service_with_cursor(cursor)
        first_result = service.get_unified_statistics()
        second_result = service.get_unified_statistics()

        assert first_result["statistics"]["total_ips"] == 1
        assert second_result["statistics"]["total_ips"] == 2

    def test_get_unified_statistics_error(self):
        db_service = Mock()
        db_service.get_connection.side_effect = Exception("db unavailable")
        service = OptimizedBlacklistService(db_service=db_service)

        result = service.get_unified_statistics()

        assert result["success"] is False
        assert "db unavailable" in result["error"]

    def test_search_ips_success(self):
        cursor = Mock()
        cursor.fetchall.return_value = [{"ip_address": "1.1.1.1", "source": "REGTECH", "country": "KR"}]
        service, _, _ = _build_service_with_cursor(cursor)

        result = service.search_ips("1.1", limit=10)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["results"][0]["ip_address"] == "1.1.1.1"

    def test_get_active_blacklist_plain_success(self):
        cursor = Mock()
        cursor.fetchall.return_value = [{"ip_address": "1.1.1.1"}, {"ip_address": "2.2.2.2"}]
        service, _, _ = _build_service_with_cursor(cursor)

        result = service.get_active_blacklist(format_type="plain")

        assert result["success"] is True
        assert result["format"] == "plain"
        assert result["ips"] == ["1.1.1.1", "2.2.2.2"]

    def test_get_active_blacklist_json_success(self):
        cursor = Mock()
        cursor.fetchall.return_value = [{"ip_address": "1.1.1.1", "source": "REGTECH"}]
        service, _, _ = _build_service_with_cursor(cursor)

        result = service.get_active_blacklist(format_type="json")

        assert result["success"] is True
        assert result["format"] == "json"
        assert result["count"] == 1

    def test_health_check_success(self):
        cursor = Mock()
        cursor.fetchone.return_value = [15]
        service, db_service, _ = _build_service_with_cursor(cursor)
        db_service.health_check.return_value = True

        result = service.health_check()

        assert result["success"] is True
        assert result["status"] == "healthy"
        assert result["total_ips"] == 15

    def test_health_check_failure(self):
        db_service = Mock()
        db_service.health_check.side_effect = Exception("failed")
        service = OptimizedBlacklistService(db_service=db_service)

        result = service.health_check()

        assert result["success"] is False
        assert result["status"] == "unhealthy"
