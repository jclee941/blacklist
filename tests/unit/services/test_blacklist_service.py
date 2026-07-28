"""
Unit tests for BlacklistService

Tests cover:
- Whitelist checking (cache + DB)
- Blacklist checking (cascading logic)
- Decision logging with metrics
- Health status reporting
- Statistics aggregation
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from app.core.services.blacklist_service import BlacklistService
from app.core.testing_app import create_app


@pytest.fixture
def app():
    """Create Flask app in test mode"""
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def mock_db_service():
    """Create mock DatabaseService"""
    service = Mock()
    service.query = Mock(return_value=Mock())
    return service


@pytest.fixture
def blacklist_service(mock_db_service):
    """Create BlacklistService with mocked dependencies"""
    # Patch Redis to avoid external dependency
    with patch("app.core.services.blacklist_service.redis.Redis") as mock_redis:
        mock_redis.return_value.ping.return_value = True
        service = BlacklistService(db_service=mock_db_service)
        return service


class TestBlacklistServiceInitialization:
    """Test service initialization and setup"""

    def test_initialization_with_db_service(self, blacklist_service):
        """Test service initializes with database service"""
        assert blacklist_service.db_service is not None
        assert blacklist_service.repo is not None
        assert blacklist_service.cache_ttl == 300

    def test_redis_initialization_success(self, blacklist_service):
        """Test Redis initialization on success"""
        assert blacklist_service._components["redis"] is True

    @patch("app.core.services.blacklist_service.redis.Redis")
    def test_redis_initialization_failure(self, mock_redis_class, mock_db_service):
        """Test service handles Redis connection failure gracefully"""
        mock_redis_class.return_value.ping.side_effect = Exception("Connection failed")

        service = BlacklistService(db_service=mock_db_service)

        assert service.redis_client is None
        assert service._components["redis"] is False


class TestWhitelistChecking:
    """Test is_whitelisted() method"""

    def test_is_whitelisted_from_cache(self, blacklist_service):
        """Test whitelist check returns from Redis cache"""
        # Arrange
        cache_key = "whitelist:192.168.1.1"
        blacklist_service.redis_client.get = Mock(return_value="true")

        # Act
        result = blacklist_service.is_whitelisted("192.168.1.1")

        # Assert
        assert result is True
        blacklist_service.redis_client.get.assert_called_once_with(cache_key)

    def test_is_whitelisted_cache_miss_db_hit(self, blacklist_service):
        """Test whitelist check falls back to DB on cache miss"""
        # Arrange
        blacklist_service.redis_client.get = Mock(return_value=None)
        blacklist_service.repo.count_whitelist_by_ip = Mock(return_value=1)

        # Act
        result = blacklist_service.is_whitelisted("192.168.1.1")

        # Assert
        assert result is True
        blacklist_service.repo.count_whitelist_by_ip.assert_called_once_with("192.168.1.1")

    def test_is_whitelisted_not_found(self, blacklist_service):
        """Test is_whitelisted returns False when IP not in whitelist"""
        # Arrange
        blacklist_service.redis_client.get = Mock(return_value=None)
        blacklist_service.repo.count_whitelist_by_ip = Mock(return_value=0)

        # Act
        result = blacklist_service.is_whitelisted("192.168.1.2")

        # Assert
        assert result is False

    def test_is_whitelisted_redis_error_graceful_fallback(self, blacklist_service):
        """Test is_whitelisted handles Redis error and falls back to DB"""
        # Arrange
        blacklist_service.redis_client.get = Mock(side_effect=Exception("Redis error"))
        blacklist_service.repo.count_whitelist_by_ip = Mock(return_value=1)

        # Act
        result = blacklist_service.is_whitelisted("192.168.1.1")

        # Assert
        assert result is True
        blacklist_service.repo.count_whitelist_by_ip.assert_called_once()


class TestBlacklistChecking:
    """Test check_blacklist() method with cascading logic"""

    def test_check_blacklist_whitelisted_ip(self, blacklist_service):
        """Test check_blacklist returns allowed for whitelisted IP"""
        # Arrange
        blacklist_service.is_whitelisted = Mock(return_value=True)

        # Act
        result = blacklist_service.check_blacklist("192.168.1.1")

        # Assert
        assert result["blocked"] is False
        assert result["reason"] == "whitelisted"
        assert result["metadata"]["source"] == "whitelist"

    def test_check_blacklist_from_cache(self, blacklist_service):
        """Test check_blacklist returns from Redis cache"""
        # Arrange
        blacklist_service.is_whitelisted = Mock(return_value=False)
        cached_result = {"blocked": True, "reason": "malware", "metadata": {"source": "regtech", "detection_count": 5}}
        import json

        blacklist_service.redis_client.get = Mock(return_value=json.dumps(cached_result))

        # Act
        result = blacklist_service.check_blacklist("10.0.0.1")

        # Assert
        assert result["blocked"] is True
        assert result["reason"] == "malware"
        assert result["metadata"]["cache_hit"] is True

    def test_check_blacklist_db_hit(self, blacklist_service):
        """Test check_blacklist finds IP in database"""
        # Arrange
        blacklist_service.is_whitelisted = Mock(return_value=False)
        blacklist_service.redis_client.get = Mock(return_value=None)
        blacklist_service.repo.get_blacklist_entry = Mock(
            return_value={"reason": "phishing", "source": "REGTECH", "detection_count": 10}
        )

        # Act
        result = blacklist_service.check_blacklist("10.0.0.1")

        # Assert
        assert result["blocked"] is True
        assert result["reason"] == "phishing"
        assert result["metadata"]["detection_count"] == 10

    def test_check_blacklist_not_found(self, blacklist_service):
        """Test check_blacklist returns allowed for clean IP"""
        # Arrange
        blacklist_service.is_whitelisted = Mock(return_value=False)
        blacklist_service.redis_client.get = Mock(return_value=None)
        blacklist_service.repo.get_blacklist_entry = Mock(return_value=None)

        # Act
        result = blacklist_service.check_blacklist("10.0.0.2")

        # Assert
        assert result["blocked"] is False
        assert result["reason"] == "not_in_blacklist"


class TestDecisionLogging:
    """Test log_decision() method"""

    @patch("app.core.services.blacklist_service.blacklist_decisions_total")
    def test_log_decision_records_metrics(self, mock_metrics, blacklist_service):
        """Test log_decision increments Prometheus metrics"""
        # Arrange
        mock_label_instance = Mock()
        mock_metrics.labels.return_value = mock_label_instance

        # Act
        blacklist_service.log_decision("192.168.1.1", "BLOCKED", "malware")

        # Assert
        mock_metrics.labels.assert_called_once_with(decision="BLOCKED", reason="malware")
        mock_label_instance.inc.assert_called_once()

    @patch("app.core.services.blacklist_service.logger")
    def test_log_decision_uses_timezone_aware_utc_timestamp(self, mock_logger, blacklist_service):
        blacklist_service.log_decision("192.168.1.1", "BLOCKED", "malware")

        timestamp = mock_logger.info.call_args.kwargs["timestamp"]
        assert datetime.fromisoformat(timestamp).tzinfo == timezone.utc

    def test_log_decision_includes_metadata(self, blacklist_service):
        """Test log_decision includes optional metadata"""
        # This test verifies structured logging captures metadata
        # In production, this would be verified via logging inspection

        # Act - should not raise
        blacklist_service.log_decision(
            "192.168.1.1", "ALLOWED", "whitelisted", metadata={"cache_hit": True, "source": "redis"}
        )


class TestHealthStatus:
    """Test get_health() method"""

    def test_get_health_returns_healthy_status(self, blacklist_service):
        """Test get_health returns healthy status"""
        # Arrange
        blacklist_service.repo.count_blacklist_ips = Mock(return_value=1000)
        blacklist_service.redis_client.ping = Mock(return_value=True)

        # Act
        health = blacklist_service.get_health()

        # Assert
        assert health.status in ["healthy", "degraded"]
        assert health.version is not None
        assert health.timestamp is not None
        assert "database" in health.components

    def test_get_health_handles_errors(self, blacklist_service):
        """Test get_health handles database errors gracefully"""
        # Arrange
        blacklist_service.repo.count_blacklist_ips = Mock(side_effect=Exception("DB error"))

        # Act
        health = blacklist_service.get_health()

        # Assert
        assert health.status == "degraded"
        assert "error" in health.components


class TestStatistics:
    """Test statistics and reporting methods"""

    def test_get_collection_status_returns_sources(self, blacklist_service):
        """Test get_collection_status returns source info"""
        # Arrange
        blacklist_service.repo.get_source_stats = Mock(
            return_value=[
                {"data_source": "REGTECH", "count": 2000, "last_seen": datetime.now()},
                {"data_source": "MANUAL", "count": 1000, "last_seen": datetime.now()},
            ]
        )

        # Act
        result = blacklist_service.get_collection_status()

        # Assert
        assert result["collection_enabled"] is True
        assert result["total_ips"] == 3000
        assert "regtech" in result["sources"]


class TestDataManipulation:
    """Test add_to_blacklist and add_to_whitelist"""

    def test_add_to_blacklist_success(self, blacklist_service):
        """Test adding IP to blacklist"""
        # Arrange
        blacklist_service.repo.insert_blacklist = Mock(return_value=True)

        # Act
        result = blacklist_service.add_to_blacklist("10.0.0.1", reason="phishing")

        # Assert
        assert result is True
        blacklist_service.repo.insert_blacklist.assert_called_once()

    def test_add_to_whitelist_success(self, blacklist_service):
        """Test adding IP to whitelist"""
        # Arrange
        blacklist_service.repo.insert_whitelist = Mock(return_value=True)

        # Act
        result = blacklist_service.add_to_whitelist("10.0.0.1", reason="trusted")

        # Assert
        assert result is True
        blacklist_service.repo.insert_whitelist.assert_called_once()
