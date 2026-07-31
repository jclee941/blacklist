"""Unit tests for Redis authentication across the Flask application.

Redis runs with ``--requirepass`` (deploy/base.yml), so every app-side Redis
client must authenticate with ``REDIS_PASSWORD`` or fail with NOAUTH.
Connections are never opened here: assertions are made on the constructed
connection parameters only.
"""

from unittest.mock import patch

import pytest

# Throwaway literals only. The specials (@ : /) prove URL encoding is applied.
PROBE_PASSWORD = "pr@be:pass/word"
ENCODED_PROBE_PASSWORD = "pr%40be%3Apass%2Fword"
TLS_QUERY = "ssl_ca_certs=%2Frun%2Fblacklist%2Fca.crt&ssl_cert_reqs=required"


@pytest.mark.unit
class TestRedisPasswordConfig:
    def test_redis_password_is_read_from_environment(self, monkeypatch):
        monkeypatch.setenv("REDIS_PASSWORD", PROBE_PASSWORD)
        from core.config import AppConfig

        assert AppConfig().REDIS_PASSWORD == PROBE_PASSWORD

    def test_redis_url_includes_credentials_when_password_is_set(self, monkeypatch):
        import redis

        monkeypatch.setenv("REDIS_HOST", "redis-host")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_PASSWORD", PROBE_PASSWORD)
        from core.config import AppConfig

        url = AppConfig().REDIS_URL

        assert url == f"rediss://:{ENCODED_PROBE_PASSWORD}@redis-host:6380?{TLS_QUERY}"
        # A real client must recover the literal password from the encoded URL.
        client = redis.Redis.from_url(url)
        assert client.connection_pool.connection_kwargs["password"] == PROBE_PASSWORD

    def test_redis_url_omits_credentials_when_password_is_absent(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "redis-host")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)
        from core.config import AppConfig

        assert AppConfig().REDIS_URL == f"rediss://redis-host:6380?{TLS_QUERY}"

        monkeypatch.setenv("REDIS_PASSWORD", "")
        assert AppConfig().REDIS_URL == f"rediss://redis-host:6380?{TLS_QUERY}"


@pytest.mark.unit
class TestRedisClientAuthentication:
    def test_cache_client_authenticates(self, monkeypatch):
        monkeypatch.setenv("REDIS_PASSWORD", PROBE_PASSWORD)
        from core.utils.cache_utils import get_redis_client

        with patch("core.utils.cache_utils.redis.Redis") as mock_redis:
            get_redis_client()

        assert mock_redis.call_args.kwargs["password"] == PROBE_PASSWORD

    def test_cache_client_verifies_tls(self, monkeypatch):
        monkeypatch.setenv("INTERNAL_CA_CERT", "/probe/ca.crt")
        from core.utils.cache_utils import get_redis_client

        with patch("core.utils.cache_utils.redis.Redis") as mock_redis:
            get_redis_client()

        assert mock_redis.call_args.kwargs["ssl"] is True
        assert mock_redis.call_args.kwargs["ssl_cert_reqs"] == "required"
        assert mock_redis.call_args.kwargs["ssl_ca_certs"] == "/probe/ca.crt"

    def test_cache_client_omits_password_when_absent(self, monkeypatch):
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)
        from core.utils.cache_utils import get_redis_client

        with patch("core.utils.cache_utils.redis.Redis") as mock_redis:
            get_redis_client()

        assert "password" not in mock_redis.call_args.kwargs

    def test_blacklist_service_client_authenticates(self, monkeypatch):
        monkeypatch.setenv("REDIS_PASSWORD", PROBE_PASSWORD)
        from core.services.blacklist_service import BlacklistService

        with patch("core.services.blacklist_service.redis.Redis") as mock_redis:
            BlacklistService()

        assert mock_redis.call_args.kwargs["password"] == PROBE_PASSWORD

    def test_blacklist_service_client_verifies_tls(self, monkeypatch):
        monkeypatch.setenv("INTERNAL_CA_CERT", "/probe/ca.crt")
        from core.services.blacklist_service import BlacklistService

        with patch("core.services.blacklist_service.redis.Redis") as mock_redis:
            BlacklistService()

        assert mock_redis.call_args.kwargs["ssl"] is True
        assert mock_redis.call_args.kwargs["ssl_cert_reqs"] == "required"
        assert mock_redis.call_args.kwargs["ssl_ca_certs"] == "/probe/ca.crt"

    def test_blacklist_service_client_omits_password_when_absent(self, monkeypatch):
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)
        from core.services.blacklist_service import BlacklistService

        with patch("core.services.blacklist_service.redis.Redis") as mock_redis:
            BlacklistService()

        assert "password" not in mock_redis.call_args.kwargs

    def test_rate_limiter_storage_uri_authenticates(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "redis-host")
        monkeypatch.setenv("REDIS_PORT", "6380")
        monkeypatch.setenv("REDIS_PASSWORD", PROBE_PASSWORD)
        from core.app import create_app

        with patch("core.app.Limiter") as mock_limiter, patch("core.app_lifecycle.threading.Thread"), patch(
            "core.services.service_factory.initialize_services", return_value={}
        ):
            create_app()

        storage_uri = mock_limiter.call_args.kwargs["storage_uri"]
        assert storage_uri == f"rediss://:{ENCODED_PROBE_PASSWORD}@redis-host:6380/1?{TLS_QUERY}"
