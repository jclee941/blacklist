"""Unit tests for app/core/routes/api/ip_management/repository.py — direct repository tests."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from core.routes.api.ip_management.repository import IPManagementRepository


def make_repo():
    """Create a repository with mocked db_service and cursor."""
    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.get_connection.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    repo = IPManagementRepository(mock_db)
    return repo, mock_conn, mock_cursor


class TestSerialize:
    def test_serialize_row_converts_datetime(self):
        repo, _, _ = make_repo()
        row = {"ip": "1.2.3.4", "created": datetime(2025, 1, 15, 10, 30, 0)}
        result = repo._serialize_row(row)
        assert result["created"] == "2025-01-15T10:30:00"
        assert result["ip"] == "1.2.3.4"

    def test_serialize_rows_handles_list(self):
        repo, _, _ = make_repo()
        rows = [
            {"ip": "1.1.1.1", "ts": datetime(2025, 1, 1)},
            {"ip": "2.2.2.2", "ts": None},
        ]
        result = repo._serialize_rows(rows)
        assert len(result) == 2
        assert result[0]["ts"] == "2025-01-01T00:00:00"
        assert result[1]["ts"] is None


class TestGetUnifiedList:
    def test_success_no_filters(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = {"total": 2}
        mock_cursor.fetchall.return_value = [
            {
                "list_type": "blacklist",
                "id": 1,
                "ip_address": "1.2.3.4",
                "reason": "malware",
                "source": "REGTECH",
                "data_source": "REGTECH",
                "confidence_level": 80,
                "detection_count": 5,
                "is_active": True,
                "country": "KR",
                "detection_date": None,
                "removal_date": None,
                "last_seen": None,
                "created_at": datetime(2025, 1, 1),
                "updated_at": datetime(2025, 1, 1),
                "auto_active": True,
            },
        ]
        items, total = repo.get_unified_list(page=1, limit=10)
        assert total == 2
        assert len(items) == 1
        assert items[0]["created_at"] == "2025-01-01T00:00:00"

    def test_with_all_filters(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = {"total": 0}
        mock_cursor.fetchall.return_value = []
        items, total = repo.get_unified_list(
            page=1,
            limit=10,
            list_type="whitelist",
            search_ip="10.0",
            is_active=True,
            source="MANUAL",
        )
        assert total == 0
        assert items == []
        # Verify params include all filters
        call_args = mock_cursor.execute.call_args_list
        assert len(call_args) == 2  # COUNT + SELECT

    def test_error_rollback(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.fetchone.side_effect = Exception("db error")
        with pytest.raises(Exception, match="db error"):
            repo.get_unified_list(page=1, limit=10)
        mock_conn.rollback.assert_called_once()


class TestGetStatistics:
    def test_success(self):
        repo, _, mock_cursor = make_repo()
        mock_cursor.fetchall.return_value = [
            {
                "list_type": "blacklist",
                "source": "REGTECH",
                "count": 100,
                "active_count": 80,
                "last_updated": datetime(2025, 6, 1),
            },
        ]
        stats = repo.get_statistics()
        assert len(stats) == 1
        assert stats[0]["count"] == 100

    def test_error_rollback(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.execute.side_effect = Exception("db")
        with pytest.raises(Exception):
            repo.get_statistics()
        mock_conn.rollback.assert_called_once()


class TestGetWhitelist:
    def test_success(self):
        repo, _, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = {"total": 1}
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "ip_address": "10.0.0.1",
                "reason": "VIP",
                "source": "MANUAL",
                "country": "US",
                "created_at": datetime(2025, 1, 1),
                "updated_at": datetime(2025, 1, 1),
            },
        ]
        items, total = repo.get_whitelist(page=1, limit=10)
        assert total == 1
        assert len(items) == 1

    def test_error_rollback(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.execute.side_effect = Exception("db")
        with pytest.raises(Exception):
            repo.get_whitelist(page=1, limit=10)
        mock_conn.rollback.assert_called_once()


class TestCreateWhitelist:
    def test_success(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "ip_address": "10.0.0.1",
            "reason": "VIP",
            "source": "MANUAL",
            "country": None,
            "created_at": datetime(2025, 1, 1),
            "updated_at": datetime(2025, 1, 1),
        }
        result = repo.create_whitelist("10.0.0.1", reason="VIP")
        assert result["ip_address"] == "10.0.0.1"
        mock_conn.commit.assert_called_once()

    def test_error_rollback(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.execute.side_effect = Exception("dup")
        with pytest.raises(Exception):
            repo.create_whitelist("10.0.0.1")
        mock_conn.rollback.assert_called_once()


class TestUpdateWhitelist:
    def test_success(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "ip_address": "10.0.0.1",
            "reason": "Updated",
            "source": "MANUAL",
            "country": None,
            "created_at": datetime(2025, 1, 1),
            "updated_at": datetime(2025, 6, 1),
        }
        result = repo.update_whitelist(1, {"reason": "Updated"})
        assert result["reason"] == "Updated"
        mock_conn.commit.assert_called_once()

    def test_not_found(self):
        repo, _, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = None
        result = repo.update_whitelist(999, {"reason": "test"})
        assert result is None

    def test_error_rollback(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.execute.side_effect = Exception("db")
        with pytest.raises(Exception):
            repo.update_whitelist(1, {"reason": "x"})
        mock_conn.rollback.assert_called_once()


class TestDeleteWhitelist:
    def test_success(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = {"ip_address": "10.0.0.1"}
        result = repo.delete_whitelist(1)
        assert result == "10.0.0.1"
        mock_conn.commit.assert_called_once()

    def test_not_found(self):
        repo, _, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = None
        result = repo.delete_whitelist(999)
        assert result is None

    def test_error_rollback(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.execute.side_effect = Exception("db")
        with pytest.raises(Exception):
            repo.delete_whitelist(1)
        mock_conn.rollback.assert_called_once()


class TestGetBlacklist:
    def test_success(self):
        repo, _, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = {"total": 1}
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "ip_address": "1.2.3.4",
                "reason": "malware",
                "source": "REGTECH",
                "data_source": "REGTECH",
                "confidence_level": 80,
                "detection_count": 5,
                "is_active": True,
                "country": "KR",
                "detection_date": datetime(2025, 1, 1),
                "removal_date": None,
                "last_seen": datetime(2025, 6, 1),
                "created_at": datetime(2025, 1, 1),
                "updated_at": datetime(2025, 6, 1),
                "auto_active": True,
            },
        ]
        items, total = repo.get_blacklist(page=1, limit=10)
        assert total == 1
        assert len(items) == 1

    def test_error_rollback(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.execute.side_effect = Exception("db")
        with pytest.raises(Exception):
            repo.get_blacklist(page=1, limit=10)
        mock_conn.rollback.assert_called_once()


class TestCreateBlacklist:
    def test_success(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "ip_address": "1.2.3.4",
            "reason": "malware",
            "source": "REGTECH",
            "data_source": "REGTECH",
            "confidence_level": 80,
            "detection_count": 1,
            "is_active": True,
            "country": "KR",
            "detection_date": datetime(2025, 1, 1),
            "removal_date": None,
            "last_seen": datetime(2025, 6, 1),
            "created_at": datetime(2025, 1, 1),
            "updated_at": datetime(2025, 1, 1),
        }
        result = repo.create_blacklist("1.2.3.4")
        assert result["ip_address"] == "1.2.3.4"
        mock_conn.commit.assert_called_once()

    def test_with_all_params(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = {
            "id": 2,
            "ip_address": "5.6.7.8",
            "reason": "phishing",
            "source": "MANUAL",
            "data_source": "MANUAL",
            "confidence_level": 90,
            "detection_count": 1,
            "is_active": True,
            "country": "US",
            "detection_date": datetime(2025, 2, 1),
            "removal_date": datetime(2025, 8, 1),
            "last_seen": datetime(2025, 2, 1),
            "created_at": datetime(2025, 2, 1),
            "updated_at": datetime(2025, 2, 1),
        }
        result = repo.create_blacklist(
            "5.6.7.8",
            reason="phishing",
            source="MANUAL",
            data_source="MANUAL",
            confidence_level=90,
            country="US",
            detection_date="2025-02-01",
            removal_date="2025-08-01",
        )
        assert result["source"] == "MANUAL"

    def test_error_rollback(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.execute.side_effect = Exception("dup")
        with pytest.raises(Exception):
            repo.create_blacklist("1.2.3.4")
        mock_conn.rollback.assert_called_once()


class TestUpdateBlacklist:
    def test_success(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "ip_address": "1.2.3.4",
            "reason": "updated",
            "source": "REGTECH",
            "data_source": "REGTECH",
            "confidence_level": 90,
            "detection_count": 5,
            "is_active": True,
            "country": "KR",
            "detection_date": None,
            "removal_date": None,
            "last_seen": None,
            "created_at": datetime(2025, 1, 1),
            "updated_at": datetime(2025, 6, 1),
        }
        result = repo.update_blacklist(1, {"reason": "updated", "confidence_level": 90})
        assert result["reason"] == "updated"
        mock_conn.commit.assert_called_once()

    def test_not_found(self):
        repo, _, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = None
        result = repo.update_blacklist(999, {"reason": "test"})
        assert result is None

    def test_ignores_invalid_columns(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "ip_address": "1.1.1.1",
            "reason": "r",
            "source": "S",
            "data_source": "D",
            "confidence_level": 50,
            "detection_count": 1,
            "is_active": True,
            "country": None,
            "detection_date": None,
            "removal_date": None,
            "last_seen": None,
            "created_at": datetime(2025, 1, 1),
            "updated_at": datetime(2025, 1, 1),
        }
        result = repo.update_blacklist(1, {"invalid_field": "x", "reason": "valid"})
        assert result is not None

    def test_error_rollback(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.execute.side_effect = Exception("db")
        with pytest.raises(Exception):
            repo.update_blacklist(1, {"reason": "x"})
        mock_conn.rollback.assert_called_once()


class TestDeleteBlacklist:
    def test_success(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = {"ip_address": "1.2.3.4"}
        result = repo.delete_blacklist(1)
        assert result == "1.2.3.4"
        mock_conn.commit.assert_called_once()

    def test_not_found(self):
        repo, _, mock_cursor = make_repo()
        mock_cursor.fetchone.return_value = None
        result = repo.delete_blacklist(999)
        assert result is None

    def test_error_rollback(self):
        repo, mock_conn, mock_cursor = make_repo()
        mock_cursor.execute.side_effect = Exception("db")
        with pytest.raises(Exception):
            repo.delete_blacklist(1)
        mock_conn.rollback.assert_called_once()
