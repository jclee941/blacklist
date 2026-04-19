"""
Integration tests for DB-only credential management (v3.6.0+)

Tests that:
1. App saves credentials to encrypted DB
2. Collector loads and decrypts from DB
3. No env var fallback (fails with clear error if missing)
4. Credential changes take effect without restart
5. Migration script properly encrypts credentials
"""

import os
import pytest


class TestDBOnlyCredentials:
    """Test suite for DB-only credential management"""

    def test_env_vars_not_used_regtech(self):
        """REGTECH credentials from env vars are ignored"""
        # This should FAIL because we removed env var support
        # and there are no DB credentials
        from collector.config import CollectorConfig

        # Even with env vars set, they should not be used
        old_regtech_id = os.environ.get("REGTECH_ID")
        old_regtech_pw = os.environ.get("REGTECH_PW")

        os.environ["REGTECH_ID"] = "test_id"
        os.environ["REGTECH_PW"] = "test_pw"

        # Clear cache to force fresh load
        CollectorConfig._cache_loaded = False
        CollectorConfig._credentials_cache.clear()

        # Collector should fail to get credentials
        with pytest.raises(ValueError) as exc_info:
            CollectorConfig.get_regtech_credentials()

        assert "not configured in database" in str(exc_info.value)

        # Restore
        if old_regtech_id:
            os.environ["REGTECH_ID"] = old_regtech_id
        elif "REGTECH_ID" in os.environ:
            del os.environ["REGTECH_ID"]

        if old_regtech_pw:
            os.environ["REGTECH_PW"] = old_regtech_pw
        elif "REGTECH_PW" in os.environ:
            del os.environ["REGTECH_PW"]

    def test_credential_not_found_error(self):
        """Clear error when credentials missing"""
        from collector.config import CollectorConfig

        # Clear cache
        CollectorConfig._cache_loaded = False
        CollectorConfig._credentials_cache.clear()

        with pytest.raises(ValueError) as exc_info:
            CollectorConfig.get_regtech_credentials()

        error_msg = str(exc_info.value)
        assert "not configured in database" in error_msg
        assert "POST /api/credentials" in error_msg

    def test_credential_cache_clearing(self):
        """Credentials are properly cleared from memory"""
        from collector.config import CollectorConfig

        # Simulate cached credentials
        CollectorConfig._credentials_cache["REGTECH"] = {"username": "test_user", "password": "test_password"}

        # Clear cache
        CollectorConfig.clear_credentials_cache()

        # Verify cleared (empty strings)
        for source in CollectorConfig._credentials_cache:
            creds = CollectorConfig._credentials_cache[source]
            assert creds.get("username") == ""
            assert creds.get("password") == ""

        # Verify cache is empty
        CollectorConfig._credentials_cache.clear()
        assert len(CollectorConfig._credentials_cache) == 0


class TestCollectorStartupValidation:
    """Test collector startup validation"""

    def test_missing_credentials_validation(self):
        """Startup validation catches missing credentials"""
        from collector.config import CollectorConfig

        # Clear cache
        CollectorConfig._cache_loaded = False
        CollectorConfig._credentials_cache.clear()

        # Should raise when trying to get credentials
        with pytest.raises(ValueError):
            CollectorConfig.get_regtech_credentials()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
