import os
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestAppConfigRedis:
    def test_redis_url_computed(self):
        env = {"REDIS_HOST": "redis-host", "REDIS_PORT": "6380"}
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            assert cfg.REDIS_URL == (
                "rediss://redis-host:6380?ssl_ca_certs=%2Frun%2Fblacklist%2Fca.crt&ssl_cert_reqs=required"
            )

    def test_get_redis_params(self):
        env = {"REDIS_HOST": "redis-host", "REDIS_PORT": "6380"}
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            cfg = AppConfig()
            params = cfg.get_redis_params()
            assert params["host"] == "redis-host"
            assert params["port"] == 6380

    def test_get_redis_params_requires_verified_tls(self):
        env = {"INTERNAL_CA_CERT": "/probe/ca.crt"}
        with patch.dict(os.environ, env, clear=True):
            from app.core.config import AppConfig

            params = AppConfig().get_redis_params()

        assert params["ssl"] is True
        assert params["ssl_cert_reqs"] == "required"
        assert params["ssl_ca_certs"] == "/probe/ca.crt"
