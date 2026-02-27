"""
#41 — _rate_limit() 동작 테스트

Tests the rate limiting mechanism in SecudiumCollector._rate_limit()
and the RateLimiter / AuthRateLimiter utility classes.
"""

import time

import pytest
from unittest.mock import MagicMock, patch

COLLECTOR_MODULE = "core.secudium_collector"


@pytest.fixture
def collector():
    with patch(f"{COLLECTOR_MODULE}.CollectorConfig") as mock_config:
        mock_config.SECUDIUM_BASE_URL = "https://test.secudium.com"
        mock_config.get_secudium_otp_config.return_value = {
            "email": "test@example.com",
            "email_password": "emailpass",
            "imap_server": "imap.test.com",
            "otp_mode": "manual",
        }

        from core.secudium_collector import SecudiumCollector

        db = MagicMock()
        c = SecudiumCollector(db_service=db)
        SecudiumCollector._cached_token = None
        SecudiumCollector._token_obtained_at = None
        yield c


@pytest.mark.unit
class TestCollectorRateLimit:
    """Tests for SecudiumCollector._rate_limit()."""

    def test_no_delay_on_first_call(self, collector):
        """First call should not sleep (no previous request time)."""
        collector._last_request_time = 0
        collector._request_delay = 1.0
        start = time.time()
        collector._rate_limit()
        elapsed = time.time() - start
        assert elapsed < 0.1  # Should be nearly instant

    def test_sleeps_when_called_too_fast(self, collector):
        """Should sleep when called within _request_delay window."""
        collector._request_delay = 0.2
        collector._last_request_time = time.time()
        start = time.time()
        collector._rate_limit()
        elapsed = time.time() - start
        assert elapsed >= 0.15  # Should have slept ~0.2s

    def test_no_sleep_after_delay_passed(self, collector):
        """Should not sleep when enough time has passed."""
        collector._request_delay = 0.1
        collector._last_request_time = time.time() - 1.0  # 1 second ago
        start = time.time()
        collector._rate_limit()
        elapsed = time.time() - start
        assert elapsed < 0.05  # No sleep needed

    def test_updates_last_request_time(self, collector):
        """Should update _last_request_time after rate limiting."""
        collector._request_delay = 0
        collector._last_request_time = 0
        before = time.time()
        collector._rate_limit()
        assert collector._last_request_time >= before

    def test_zero_delay_no_sleep(self, collector):
        """With zero delay, should never sleep."""
        collector._request_delay = 0
        collector._last_request_time = time.time()
        start = time.time()
        collector._rate_limit()
        elapsed = time.time() - start
        assert elapsed < 0.05


@pytest.mark.unit
class TestRateLimiterClass:
    """Tests for the standalone RateLimiter class."""

    def test_acquire_success(self):
        from core.rate_limiter import RateLimiter

        rl = RateLimiter(requests_per_second=10.0, burst_size=5)
        assert rl.acquire() is True

    def test_burst_limit(self):
        from core.rate_limiter import RateLimiter

        rl = RateLimiter(requests_per_second=1.0, burst_size=3)
        # Should succeed for burst_size calls
        for _ in range(3):
            assert rl.acquire(timeout=0) is True

    def test_backoff_on_failure(self):
        from core.rate_limiter import RateLimiter

        rl = RateLimiter(requests_per_second=10.0, burst_size=5, backoff_factor=2.0)
        with patch("time.sleep"):
            rl.on_failure(429)
        stats = rl.get_stats()
        assert stats["failure_count"] > 0

    def test_reset_on_success(self):
        from core.rate_limiter import RateLimiter

        rl = RateLimiter(requests_per_second=10.0, burst_size=5)
        with patch("time.sleep"):
            rl.on_failure(500)
        rl.on_success()
        stats = rl.get_stats()
        assert stats["failure_count"] == 0

    def test_get_stats(self):
        from core.rate_limiter import RateLimiter

        rl = RateLimiter(requests_per_second=5.0, burst_size=3)
        stats = rl.get_stats()
        assert "current_tokens" in stats
        assert "failure_count" in stats

    def test_reset(self):
        from core.rate_limiter import RateLimiter

        rl = RateLimiter(requests_per_second=5.0, burst_size=3)
        with patch("time.sleep"):
            rl.on_failure(500)
        rl.reset()
        stats = rl.get_stats()
        assert stats["failure_count"] == 0


@pytest.mark.unit
class TestAuthRateLimiter:
    """Tests for AuthRateLimiter with lockout behavior."""

    def test_lockout_after_max_failures(self):
        from core.rate_limiter import AuthRateLimiter

        with patch("time.sleep"):
            rl = AuthRateLimiter(requests_per_second=100.0, max_attempts=3, lockout_duration=10.0)
            for _ in range(3):
                rl.on_failure(401)
            # After max_attempts failures, should be locked
            assert rl.locked_until is not None
            assert rl.locked_until > time.time()

    def test_success_resets_lockout(self):
        from core.rate_limiter import AuthRateLimiter

        with patch("time.sleep"):
            rl = AuthRateLimiter(requests_per_second=100.0, max_attempts=3, lockout_duration=10.0)
            rl.on_failure(401)
            rl.on_success()
            assert rl.consecutive_failures == 0

    def test_wait_if_needed_when_not_locked(self):
        from core.rate_limiter import AuthRateLimiter

        rl = AuthRateLimiter(requests_per_second=100.0, max_attempts=3, lockout_duration=10.0)
        # Should not raise or block significantly
        start = time.time()
        rl.wait_if_needed()
        elapsed = time.time() - start
        assert elapsed < 1.0
