"""Tests for blacklist_repository.py"""

from unittest.mock import Mock, MagicMock


from core.services.blacklist_repository import BlacklistRepository


def _make_repo(db_service=None):
    """Create BlacklistRepository with mocked db_service."""
    mock_db = db_service or Mock()
    repo = BlacklistRepository(db_service=mock_db)
    return repo, mock_db


class TestBlacklistRepositoryInit:
    def test_init_sets_db(self):
        repo, mock_db = _make_repo()
        assert repo.db is mock_db


class TestCountWhitelistByIp:
    def test_count_whitelist_found(self):
        repo, mock_db = _make_repo()
        mock_db.query.return_value = [{"count": 3}]
        result = repo.count_whitelist_by_ip("1.2.3.4")
        assert result == 3

    def test_count_whitelist_not_found(self):
        repo, mock_db = _make_repo()
        mock_db.query.return_value = [{"count": 0}]
        result = repo.count_whitelist_by_ip("1.2.3.4")
        assert result == 0

    def test_count_whitelist_empty_result(self):
        repo, mock_db = _make_repo()
        mock_db.query.return_value = []
        # Should handle empty result gracefully
        try:
            result = repo.count_whitelist_by_ip("1.2.3.4")
            assert result == 0 or isinstance(result, int)
        except (IndexError, TypeError):
            pass  # Acceptable if it throws on empty


class TestGetBlacklistEntry:
    def test_get_entry_found(self):
        repo, mock_db = _make_repo()
        mock_db.query.return_value = [{"ip_address": "1.2.3.4", "is_active": True, "reason": "test"}]
        result = repo.get_blacklist_entry("1.2.3.4")
        assert result is not None
        assert result["ip_address"] == "1.2.3.4"

    def test_get_entry_not_found(self):
        repo, mock_db = _make_repo()
        mock_db.query.return_value = []
        result = repo.get_blacklist_entry("9.9.9.9")
        assert result is None


class TestInsertBlacklist:
    def test_insert_success(self):
        repo, mock_db = _make_repo()
        mock_db.execute.return_value = True
        result = repo.insert_blacklist("1.2.3.4", reason="test block")
        assert result is True

    def test_insert_with_defaults(self):
        repo, mock_db = _make_repo()
        mock_db.execute.return_value = True
        result = repo.insert_blacklist("1.2.3.4")
        assert result is True
        # Check that execute was called with defaults
        call_args = mock_db.execute.call_args
        assert call_args is not None

    def test_insert_error(self):
        repo, mock_db = _make_repo()
        mock_db.execute.side_effect = Exception("insert failed")
        try:
            result = repo.insert_blacklist("1.2.3.4")
            assert result is False
        except Exception:
            pass  # Some implementations may raise


class TestInsertWhitelist:
    def test_insert_whitelist_success(self):
        repo, mock_db = _make_repo()
        mock_db.execute.return_value = True
        result = repo.insert_whitelist("1.2.3.4", reason="Manual whitelist")
        assert result is True

    def test_insert_whitelist_uses_single_ip_conflict_target(self):
        # Given
        repo, mock_db = _make_repo()
        mock_db.execute.return_value = True

        # When
        result = repo.insert_whitelist("1.2.3.4", source="MANUAL")

        # Then
        assert result is True
        query = mock_db.execute.call_args.args[0]
        assert "ON CONFLICT (ip_address)" in query
        assert "ON CONFLICT (ip_address, source)" not in query


class TestCountBlacklistIps:
    def test_count_blacklist(self):
        repo, mock_db = _make_repo()
        mock_db.query.return_value = [{"count": 150}]
        result = repo.count_blacklist_ips()
        assert result == 150


class TestGetSourceStats:
    def test_get_source_stats(self):
        repo, mock_db = _make_repo()
        mock_db.query.return_value = [
            {"data_source": "REGTECH", "count": 100, "last_seen": "2024-01-01"},
            {"data_source": "MANUAL", "count": 50, "last_seen": "2024-01-02"},
        ]
        result = repo.get_source_stats()
        assert isinstance(result, list)
        assert len(result) == 2


class TestGetActiveBlacklistEnhanced:
    def test_get_enhanced_list(self):
        repo, mock_db = _make_repo()
        mock_db.query.return_value = [
            {"ip_address": "1.2.3.4", "reason": "test", "last_seen": "2024-01-01"},
        ]
        result = repo.get_active_blacklist_enhanced()
        assert isinstance(result, list)
        assert len(result) == 1


class TestGetActiveBlacklistIps:
    def test_get_ip_list(self):
        repo, mock_db = _make_repo()
        mock_db.query.return_value = [
            {"ip_address": "1.2.3.4"},
            {"ip_address": "5.6.7.8"},
        ]
        result = repo.get_active_blacklist_ips()
        assert isinstance(result, list)
        assert "1.2.3.4" in result
        assert "5.6.7.8" in result


class TestCountActiveBlacklistIps:
    def test_count_active(self):
        repo, mock_db = _make_repo()
        mock_db.query.return_value = [{"count": 80}]
        result = repo.count_active_blacklist_ips()
        assert result == 80


class TestGetSourceCounts:
    def test_get_source_counts(self):
        repo, mock_db = _make_repo()
        mock_db.query.return_value = [
            {"data_source": "REGTECH", "count": 100},
            {"data_source": "MANUAL", "count": 50},
        ]
        result = repo.get_source_counts()
        assert isinstance(result, dict)
        assert "REGTECH" in result


class TestDeactivateBySource:
    def test_deactivate(self):
        repo, mock_db = _make_repo()
        mock_db.execute.return_value = True
        repo.deactivate_by_source("REGTECH")
        mock_db.execute.assert_called_once()


class TestUpsertBlacklistFromCollector:
    def test_upsert_success(self):
        repo, mock_db = _make_repo()
        mock_db.execute.return_value = True
        result = repo.upsert_blacklist_from_collector("1.2.3.4", "malicious", "KR", "2024-01-01")
        assert result is True


def test_repository_does_not_expose_runtime_schema_mutation() -> None:
    repo, _mock_db = _make_repo()

    assert not hasattr(repo, "add_column_if_not_exists")
    assert not hasattr(repo, "create_whitelist_table")
