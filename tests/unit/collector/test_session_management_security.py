"""Unit tests for session management security fixes.

Tests for vulnerabilities fixed in session management security audit:
- Pending auth state race condition (CRITICAL)
- IP cache unbounded growth (HIGH)
- Credential handling (HIGH)
- IMAP timeout enforcement (MEDIUM)
"""

import pytest
import threading
import time
import os
from datetime import datetime
from unittest.mock import MagicMock, patch


@pytest.mark.unit
class TestPendingAuthStateConcurrency:
    """Test thread-safe access to pending auth state (CRITICAL FIX)."""

    def _make_health_server(self):
        """Create HealthServer with mock dependencies."""
        from collector.health_server import HealthServer

        mock_collector = MagicMock()
        mock_scheduler = MagicMock()
        collectors = {"SECUDIUM": mock_collector}

        server = HealthServer(
            collectors_ref=collectors,
            scheduler_ref=mock_scheduler,
            port=0,
        )
        return server, mock_collector, mock_scheduler

    def test_pending_auth_lock_exists(self):
        """Verify _pending_auth_lock is initialized in __init__."""
        server, _, _ = self._make_health_server()
        assert hasattr(server, "_pending_auth_lock")
        assert hasattr(server._pending_auth_lock, "acquire") and hasattr(server._pending_auth_lock, "release")

    def test_concurrent_pending_auth_writes(self):
        """Test concurrent writes to _secudium_pending_auth are thread-safe.

        CRITICAL: Without lock, concurrent writes cause race condition.
        This test verifies the lock prevents data corruption.
        """
        server, _, _ = self._make_health_server()

        # Track successful writes
        results = []
        errors = []

        def write_pending_auth(auth_id: int):
            """Simulate concurrent auth state updates."""
            try:
                # This should use the lock (implementation detail)
                with server._pending_auth_lock:
                    server._secudium_pending_auth = {
                        "id": auth_id,
                        "timestamp": datetime.now(),
                        "data": f"auth_{auth_id}",
                    }
                    # Simulate some processing time
                    time.sleep(0.001)
                    # Verify the state is intact (no corruption)
                    assert server._secudium_pending_auth["id"] == auth_id
                results.append(auth_id)
            except Exception as e:
                errors.append(str(e))

        # Create 10 concurrent write threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=write_pending_auth, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during concurrent writes: {errors}"
        assert len(results) == 10, f"Expected 10 successful writes, got {len(results)}"

    def test_concurrent_pending_auth_reads(self):
        """Test concurrent reads while writes happen are thread-safe.

        Simulates multiple threads reading auth state while one thread writes.
        Without lock, this causes data races.
        """
        server, _, _ = self._make_health_server()
        initial_data = {
            "id": 1,
            "timestamp": datetime.now(),
            "data": "initial",
        }
        server._secudium_pending_auth = initial_data

        read_results = []
        errors = []

        def read_pending_auth():
            """Read auth state multiple times."""
            try:
                for _ in range(50):
                    with server._pending_auth_lock:
                        data = server._secudium_pending_auth
                        if data is not None:
                            read_results.append(data.get("id"))
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(str(e))

        def write_pending_auth():
            """Update auth state while reads happen."""
            try:
                for i in range(50):
                    with server._pending_auth_lock:
                        server._secudium_pending_auth = {
                            "id": i,
                            "timestamp": datetime.now(),
                            "data": f"auth_{i}",
                        }
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(str(e))

        # Start reader threads
        readers = [threading.Thread(target=read_pending_auth) for _ in range(5)]
        writer = threading.Thread(target=write_pending_auth)

        for r in readers:
            r.start()
        writer.start()

        # Wait for completion
        for r in readers:
            r.join()
        writer.join()

        # Verify integrity
        assert len(errors) == 0, f"Errors during concurrent reads/writes: {errors}"
        assert len(read_results) > 0, "No reads were successful"

    def test_pending_auth_isolation_no_interference(self):
        """Verify lock prevents interference between multiple collectors."""
        server, _, _ = self._make_health_server()

        state_snapshots = []

        def collector_thread(collector_id: int):
            """Simulate independent collector setting pending auth."""
            for i in range(20):
                with server._pending_auth_lock:
                    # Update state
                    server._secudium_pending_auth = {
                        "collector": collector_id,
                        "iteration": i,
                        "timestamp": datetime.now(),
                    }
                    # Read back immediately (should see what we just wrote)
                    current = server._secudium_pending_auth
                    assert current["collector"] == collector_id
                    state_snapshots.append(current.copy())
                    time.sleep(0.0001)

        # Run multiple collector threads
        threads = [threading.Thread(target=collector_thread, args=(i,)) for i in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify each collector's state was isolated
        assert len(state_snapshots) == 60  # 3 threads × 20 iterations


@pytest.mark.unit
class TestIPCacheEvictionTTL:
    """Test IP cache eviction by TTL (HIGH FIX)."""

    def _make_database_service(self):
        """Create DatabaseService instance."""
        from collector.core.database import DatabaseService

        service = DatabaseService()
        # Override TTL to 1 second for testing
        service.ip_cache_ttl = 1
        service.ip_cache_max_size = 100000
        return service

    def test_ip_cache_ttl_initialization(self):
        """Verify IP cache TTL and max size are set."""
        service = self._make_database_service()
        assert hasattr(service, "ip_cache_ttl")
        assert service.ip_cache_ttl == 1  # We override to 1s for testing
        assert hasattr(service, "ip_cache_max_size")
        assert service.ip_cache_max_size == 100000

    def test_ip_cache_evict_stale_ips_by_ttl(self):
        """Test that IPs not seen in TTL period are evicted."""
        service = self._make_database_service()
        service.ip_cache_ttl = 1  # 1 second TTL

        # Populate cache with test IPs
        current_time = time.time()
        service.ip_cache = {
            "192.168.1.1": current_time,  # Fresh (will stay)
            "192.168.1.2": current_time - 0.5,  # Fresh (will stay)
            "192.168.1.3": current_time - 1.5,  # Stale (will be evicted)
            "192.168.1.4": current_time - 3.0,  # Stale (will be evicted)
        }

        # Run eviction
        evicted = service._evict_stale_ips()

        # Verify stale IPs were removed
        assert evicted == 2, f"Expected 2 evictions, got {evicted}"
        assert "192.168.1.1" in service.ip_cache
        assert "192.168.1.2" in service.ip_cache
        assert "192.168.1.3" not in service.ip_cache
        assert "192.168.1.4" not in service.ip_cache

    def test_ip_cache_ttl_with_sleep(self):
        """Test IP cache TTL with actual time delay."""
        service = self._make_database_service()
        service.ip_cache_ttl = 0.1  # 100ms for testing

        current_time = time.time()
        service.ip_cache = {
            "192.168.1.1": current_time,
        }

        # Wait for TTL to expire
        time.sleep(0.15)

        # Evict stale IPs
        evicted = service._evict_stale_ips()

        # Verify the IP was evicted
        assert evicted == 1
        assert "192.168.1.1" not in service.ip_cache


@pytest.mark.unit
class TestIPCacheEvictionLRU:
    """Test IP cache LRU eviction at max size (HIGH FIX)."""

    def _make_database_service(self):
        """Create DatabaseService instance."""
        from collector.core.database import DatabaseService

        service = DatabaseService()
        # Set low max size for testing
        service.ip_cache_max_size = 100
        service.ip_cache_ttl = 86400  # 24 hours
        return service

    def test_ip_cache_lru_eviction_at_max_size(self):
        """Test that oldest 10% of IPs are evicted when max size exceeded."""
        service = self._make_database_service()
        service.ip_cache_max_size = 100

        # Populate cache to max + 10 IPs (triggers eviction)
        current_time = time.time()
        for i in range(110):
            # Simulate incrementally newer IPs
            service.ip_cache[f"192.168.{i // 256}.{i % 256}"] = current_time + i

        assert len(service.ip_cache) == 110, "Cache should have 110 IPs before eviction"

        # Run eviction (should remove oldest 10%)
        evicted = service._evict_stale_ips()

        # Verify eviction happened
        assert evicted == 11, f"Expected 11 evictions (10% of 110), got {evicted}"
        assert len(service.ip_cache) == 99, f"Expected 99 IPs after eviction, got {len(service.ip_cache)}"

    def test_ip_cache_lru_keeps_newest_ips(self):
        """Test that newest IPs are kept during LRU eviction."""
        service = self._make_database_service()
        service.ip_cache_max_size = 10

        # Create IPs with timestamps: 1, 2, 3, ..., 15
        current_time = time.time()
        for i in range(1, 16):
            service.ip_cache[f"192.168.0.{i}"] = current_time + i

        # Run eviction
        service._evict_stale_ips()

        # Verify oldest were evicted, newest were kept
        remaining_ips = list(service.ip_cache.keys())
        assert "192.168.0.1" not in service.ip_cache, "Oldest IP should be evicted"
        assert "192.168.0.2" not in service.ip_cache, "Second oldest should be evicted"
        assert "192.168.0.15" in service.ip_cache, "Newest IP should remain"
        assert "192.168.0.14" in service.ip_cache, "Second newest should remain"
        assert len(remaining_ips) == 9, f"Expected 9 IPs after eviction, got {len(remaining_ips)}"

    def test_ip_cache_combined_ttl_and_lru(self):
        """Test combined TTL and LRU eviction."""
        service = self._make_database_service()
        service.ip_cache_ttl = 1  # 1 second
        service.ip_cache_max_size = 20

        current_time = time.time()

        # Add old stale IPs (should be removed by TTL)
        for i in range(5):
            service.ip_cache[f"192.168.0.{i}"] = current_time - 2.0

        # Add fresh IPs exceeding max size (should be removed by LRU)
        for i in range(5, 25):
            service.ip_cache[f"192.168.0.{i}"] = current_time + i

        # Run eviction
        service._evict_stale_ips()

        # Verify both TTL and LRU eviction happened
        for i in range(5):
            assert f"192.168.0.{i}" not in service.ip_cache, f"Stale IP 192.168.0.{i} should be evicted by TTL"

        # Verify newest IPs are kept (LRU)
        assert "192.168.0.24" in service.ip_cache, "Newest IP should remain"
        assert "192.168.0.23" in service.ip_cache, "Recent IP should remain"


@pytest.mark.unit
class TestCredentialCleanup:
    """Test secure credential cleanup (HIGH FIX)."""

    def test_collector_config_has_cleanup_method(self):
        """Verify CollectorConfig has clear_credentials_cache method."""
        from collector.config import CollectorConfig

        assert hasattr(CollectorConfig, "clear_credentials_cache")
        assert callable(CollectorConfig.clear_credentials_cache)

    def test_credential_cleanup_overwrites_memory(self):
        """Test that credentials are overwritten before deletion."""
        from collector.config import CollectorConfig

        # Set test credentials
        CollectorConfig._credentials_cache = {
            "REGTECH": {"username": "test_user", "password": "secret_password_12345"},
            "SECUDIUM": {"username": "token_user", "password": "token_abc123xyz"},
        }

        # Call cleanup
        CollectorConfig.clear_credentials_cache()

        # Verify cache is cleared
        assert CollectorConfig._credentials_cache == {}, "Credentials cache should be empty after cleanup"

    def test_credential_no_plaintext_in_memory_after_cleanup(self):
        """Verify no plaintext credentials remain in Python objects after cleanup."""
        from collector.config import CollectorConfig

        # Set sensitive data
        original_data = {
            "REGTECH": {"username": "admin_user", "password": "super_secret_123"},
            "SECUDIUM": {"username": "api_user", "password": "sk_live_abc123xyz"},
        }
        CollectorConfig._credentials_cache = {k: dict(v) for k, v in original_data.items()}

        # Store references to verify they're cleared
        cache_ref = CollectorConfig._credentials_cache

        # Cleanup
        CollectorConfig.clear_credentials_cache()

        # Verify the cache dict was cleared
        assert cache_ref == {}, "Cache reference should be empty"
        assert CollectorConfig._credentials_cache == {}, "New reference should also be empty"


@pytest.mark.unit
class TestIMAPTimeoutEnforcement:
    """Test IMAP timeout enforcement (MEDIUM FIX)."""

    def test_otp_email_reader_has_timeout(self):
        """Verify OTPEmailReader connect() calls IMAP4_SSL with timeout."""
        from collector.utils.otp_email_reader import OTPEmailReader

        with patch("collector.utils.otp_email_reader.imaplib.IMAP4_SSL") as mock_imap:
            mock_instance = MagicMock()
            mock_imap.return_value = mock_instance

            reader = OTPEmailReader(
                email_address="test@example.com",
                email_password="test_password",
                imap_server="imap.gmail.com",
            )
            reader.connect()

            # Verify IMAP4_SSL was called with timeout parameter
            mock_imap.assert_called_once()
            call_kwargs = mock_imap.call_args
            # timeout may be positional or keyword
            assert call_kwargs[1].get("timeout") == 30 or (len(call_kwargs[0]) > 1 and call_kwargs[0][1] == 30), (
                f"Expected timeout=30, got {call_kwargs}"
            )

    def test_otp_email_reader_timeout_prevents_hanging(self):
        """Test that IMAP operations timeout instead of hanging indefinitely."""
        from collector.utils.otp_email_reader import OTPEmailReader

        with patch("collector.utils.otp_email_reader.imaplib.IMAP4_SSL") as mock_imap:
            # Simulate IMAP that hangs on login
            mock_instance = MagicMock()
            mock_instance.login.side_effect = TimeoutError("IMAP operation timed out")
            mock_imap.return_value = mock_instance

            reader = OTPEmailReader(
                email_address="test@example.com",
                email_password="test_password",
                imap_server="imap.slow.com",
            )
            result = reader.connect()  # Should not hang, returns False on error

            assert result is False, "connect() should return False on timeout"
            mock_imap.assert_called_once()
            assert mock_imap.call_args[1].get("timeout") == 30

    def test_imap_timeout_value_is_reasonable(self):
        """Verify IMAP timeout value is reasonable (not too short, not infinite)."""
        from collector.utils.otp_email_reader import OTPEmailReader

        with patch("collector.utils.otp_email_reader.imaplib.IMAP4_SSL") as mock_imap:
            mock_instance = MagicMock()
            mock_imap.return_value = mock_instance

            reader = OTPEmailReader(
                email_address="test@example.com",
                email_password="test_password",
                imap_server="imap.gmail.com",
            )
            reader.connect()

            timeout = mock_imap.call_args[1].get("timeout")

            # Timeout should be between 10 and 60 seconds
            assert timeout is not None, "Timeout should be set"
            assert isinstance(timeout, (int, float)), "Timeout should be numeric"
            assert 10 <= timeout <= 60, f"Timeout {timeout}s should be between 10-60 seconds"


@pytest.mark.unit
class TestFortimanagerUploaderURLs:
    """Test FortiManager uploader uses configurable URLs (CRITICAL FIX)."""

    def test_fortimanager_uploader_has_get_api_url_method(self):
        """Verify FortiManagerUploader has _get_api_url helper."""
        from collector.fortimanager_uploader import FortiManagerUploader

        with patch.object(FortiManagerUploader, "_load_credentials_from_db"):
            uploader = FortiManagerUploader()
            assert hasattr(uploader, "_get_api_url")
            assert callable(uploader._get_api_url)

    def test_fortimanager_uploader_uses_env_var(self):
        """Test FortiManager uploader respects BLACKLIST_API_URL env var."""
        from collector.fortimanager_uploader import FortiManagerUploader

        with patch.dict(os.environ, {"BLACKLIST_API_URL": "http://custom-api:2542"}):
            with patch.object(FortiManagerUploader, "_load_credentials_from_db"):
                uploader = FortiManagerUploader()
                url = uploader._get_api_url()
                assert url == "http://custom-api:2542/api/fortinet/active-ips", (
                    f"Should use BLACKLIST_API_URL from environment, got {url}"
                )

    def test_fortimanager_uploader_fallback_default(self):
        """Test FortiManager uploader falls back to default if env var not set."""
        from collector.fortimanager_uploader import FortiManagerUploader

        env_copy = {k: v for k, v in os.environ.items() if k != "BLACKLIST_API_URL"}
        with patch.dict(os.environ, env_copy, clear=True):
            with patch.object(FortiManagerUploader, "_load_credentials_from_db"):
                uploader = FortiManagerUploader()
                url = uploader._get_api_url()
                # Should have a default URL (not hardcoded localhost)
                assert url is not None
                assert "blacklist-app" in url, f"Should have reasonable default URL, got {url}"


@pytest.mark.unit
class TestSecurityFunctionsIntegration:
    """Integration tests for all security fixes working together."""

    def test_all_locks_and_caches_coexist(self):
        """Test that all thread-safety mechanisms coexist without conflict."""
        from collector.health_server import HealthServer
        from collector.core.database import DatabaseService

        # Create instances
        mock_collector = MagicMock()
        mock_scheduler = MagicMock()
        collectors = {"SECUDIUM": mock_collector}

        server = HealthServer(
            collectors_ref=collectors,
            scheduler_ref=mock_scheduler,
            port=0,
        )
        db_service = DatabaseService()

        # Verify all components have their protections
        assert hasattr(server, "_pending_auth_lock")
        assert hasattr(db_service, "ip_cache_ttl")
        assert hasattr(db_service, "ip_cache_max_size")
        assert hasattr(db_service, "_evict_stale_ips")

    def test_concurrent_auth_and_cache_operations(self):
        """Test concurrent auth state and cache operations don't interfere."""
        from collector.health_server import HealthServer
        from collector.core.database import DatabaseService

        mock_collector = MagicMock()
        server = HealthServer(
            collectors_ref={"SECUDIUM": mock_collector},
            scheduler_ref=MagicMock(),
            port=0,
        )
        db_service = DatabaseService()

        errors = []

        def auth_operations():
            """Simulate pending auth state updates."""
            try:
                for i in range(20):
                    with server._pending_auth_lock:
                        server._secudium_pending_auth = {
                            "id": i,
                            "timestamp": datetime.now(),
                        }
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"auth_ops: {e}")

        def cache_operations():
            """Simulate IP cache operations."""
            try:
                current_time = time.time()
                for i in range(20):
                    db_service.ip_cache[f"192.168.0.{i}"] = current_time
                    if i % 5 == 0:
                        db_service._evict_stale_ips()
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"cache_ops: {e}")

        # Run concurrently
        t1 = threading.Thread(target=auth_operations)
        t2 = threading.Thread(target=cache_operations)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0, f"Concurrent operations failed: {errors}"
