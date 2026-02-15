"""IPExpiryService 유닛 테스트"""

import pytest
from datetime import date
from unittest.mock import Mock, patch

from app.core.services.expiry_service import IPExpiryService


@pytest.mark.unit
class TestCheckAndDeactivateExpiredIps:
    """check_and_deactivate_expired_ips 테스트"""

    def setup_method(self):
        self.mock_db = Mock()
        self.service = IPExpiryService(db_service=self.mock_db)

    def test_no_expired_ips(self):
        """만료된 IP 없는 경우"""
        self.mock_db.query.return_value = []

        result = self.service.check_and_deactivate_expired_ips()

        assert result["success"] is True
        assert result["expired_count"] == 0
        assert "만료된 IP가 없습니다" in result["message"]

    def test_expired_ips_deactivated(self):
        """만료된 IP 비활성화"""
        expired_records = [
            {"id": 1, "ip_address": "1.2.3.4", "source": "REGTECH", "removal_date": date(2024, 1, 1)},
            {"id": 2, "ip_address": "5.6.7.8", "source": "manual", "removal_date": date(2024, 6, 15)},
        ]
        self.mock_db.query.return_value = expired_records
        self.mock_db.execute.return_value = 2

        result = self.service.check_and_deactivate_expired_ips()

        assert result["success"] is True
        assert result["expired_count"] == 2
        assert len(result["expired_ips"]) == 2
        assert result["expired_ips"][0]["ip_address"] == "1.2.3.4"
        assert result["expired_ips"][1]["ip_address"] == "5.6.7.8"
        self.mock_db.execute.assert_called_once()

    def test_db_query_called_with_today(self):
        """쿼리에 오늘 날짜 전달 확인"""
        self.mock_db.query.return_value = []

        self.service.check_and_deactivate_expired_ips()

        call_args = self.mock_db.query.call_args
        assert call_args is not None
        # 두 번째 인자(params)의 첫 번째 값이 오늘 날짜
        assert call_args[0][1] == (date.today(),)

    def test_db_error_returns_failure(self):
        """DB 에러 시 실패 반환"""
        self.mock_db.query.side_effect = Exception("Connection failed")

        result = self.service.check_and_deactivate_expired_ips()

        assert result["success"] is False
        assert "Connection failed" in result["error"]
        assert result["expired_count"] == 0

    def test_expired_ips_response_format(self):
        """응답 포맷 검증"""
        self.mock_db.query.return_value = [
            {"id": 1, "ip_address": "10.0.0.1", "source": "REGTECH", "removal_date": date(2024, 3, 15)},
        ]
        self.mock_db.execute.return_value = 1

        result = self.service.check_and_deactivate_expired_ips()

        ip_info = result["expired_ips"][0]
        assert "ip_address" in ip_info
        assert "source" in ip_info
        assert "removal_date" in ip_info
        assert ip_info["removal_date"] == "2024-03-15"

    def test_none_removal_date_handled(self):
        """removal_date가 None인 경우"""
        self.mock_db.query.return_value = [
            {"id": 1, "ip_address": "10.0.0.1", "source": "REGTECH", "removal_date": None},
        ]
        self.mock_db.execute.return_value = 1

        result = self.service.check_and_deactivate_expired_ips()

        assert result["expired_ips"][0]["removal_date"] is None


@pytest.mark.unit
class TestGetExpiryStats:
    """get_expiry_stats 테스트"""

    def setup_method(self):
        self.mock_db = Mock()
        self.service = IPExpiryService(db_service=self.mock_db)

    def test_stats_returned(self):
        self.mock_db.query.return_value = [
            {
                "total_ips": 100,
                "active_ips": 80,
                "inactive_ips": 20,
                "pending_expiry": 5,
                "future_expiry": 10,
            }
        ]

        result = self.service.get_expiry_stats()

        assert result["success"] is True
        assert result["total_ips"] == 100
        assert result["active_ips"] == 80
        assert result["inactive_ips"] == 20
        assert result["pending_expiry"] == 5
        assert result["future_expiry"] == 10
        assert result["check_date"] == date.today().isoformat()

    def test_empty_result(self):
        self.mock_db.query.return_value = []

        result = self.service.get_expiry_stats()

        assert result["success"] is True
        assert result["total_ips"] == 0

    def test_db_error(self):
        self.mock_db.query.side_effect = Exception("DB error")

        result = self.service.get_expiry_stats()

        assert result["success"] is False
        assert "DB error" in result["error"]


@pytest.mark.unit
class TestManuallyExpireIp:
    """manually_expire_ip 테스트"""

    def setup_method(self):
        self.mock_db = Mock()
        self.service = IPExpiryService(db_service=self.mock_db)

    def test_expire_existing_active_ip(self):
        self.mock_db.query.side_effect = [
            [{"id": 1, "ip_address": "1.2.3.4", "source": "REGTECH", "is_active": True}],
            None,  # UPDATE 쿼리
        ]

        result = self.service.manually_expire_ip("1.2.3.4")

        assert result["success"] is True
        assert "1.2.3.4" in result["message"]

    def test_ip_not_found(self):
        self.mock_db.query.return_value = []

        result = self.service.manually_expire_ip("1.2.3.4")

        assert result["success"] is False
        assert "찾을 수 없습니다" in result["error"]

    def test_already_inactive(self):
        self.mock_db.query.return_value = [{"id": 1, "ip_address": "1.2.3.4", "source": "REGTECH", "is_active": False}]

        result = self.service.manually_expire_ip("1.2.3.4")

        assert result["success"] is False
        assert "이미 비활성화" in result["error"]

    def test_expire_with_source_filter(self):
        self.mock_db.query.side_effect = [
            [{"id": 1, "ip_address": "1.2.3.4", "source": "REGTECH", "is_active": True}],
            None,
        ]

        result = self.service.manually_expire_ip("1.2.3.4", source="REGTECH")

        assert result["success"] is True
        # source 파라미터로 쿼리했는지 확인
        first_query_args = self.mock_db.query.call_args_list[0]
        assert "source" in first_query_args[0][0]

    def test_db_error_handled(self):
        self.mock_db.query.side_effect = Exception("Connection timeout")

        result = self.service.manually_expire_ip("1.2.3.4")

        assert result["success"] is False
        assert "Connection timeout" in result["error"]
