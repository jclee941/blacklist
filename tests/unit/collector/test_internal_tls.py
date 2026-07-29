from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import redis

from collector.config import CollectorConfig
from collector.core.database.service import DatabaseService
from collector.core.policy_monitor import REGTECHPolicyMonitor


def test_collector_postgres_params_require_verified_tls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(CollectorConfig, "INTERNAL_CA_CERT", "/probe/ca.crt")

    params = getattr(CollectorConfig, "get_postgres_connection_params")()

    assert params["sslmode"] == "verify-full"
    assert params["sslrootcert"] == "/probe/ca.crt"


def test_credential_loader_forwards_postgres_tls(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = MagicMock()
    connection.cursor.return_value.fetchall.return_value = []
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr("collector.config.psycopg2.connect", connect)
    monkeypatch.setattr(CollectorConfig, "_credentials_cache", {})
    monkeypatch.setattr(CollectorConfig, "_cache_loaded", False)
    monkeypatch.setattr(CollectorConfig, "INTERNAL_CA_CERT", "/probe/ca.crt")

    CollectorConfig._load_credentials_from_db()

    assert connect.call_args.kwargs["sslmode"] == "verify-full"
    assert connect.call_args.kwargs["sslrootcert"] == "/probe/ca.crt"


def test_collector_database_pool_forwards_postgres_tls(monkeypatch: pytest.MonkeyPatch) -> None:
    connection_pool = MagicMock()
    pool_factory = MagicMock(return_value=connection_pool)
    monkeypatch.setattr("collector.core.database.service.SimpleConnectionPool", pool_factory)
    monkeypatch.setattr(CollectorConfig, "INTERNAL_CA_CERT", "/probe/ca.crt")
    service = DatabaseService()

    service._initialize_connection_pool()

    assert pool_factory.call_args.kwargs["sslmode"] == "verify-full"
    assert pool_factory.call_args.kwargs["sslrootcert"] == "/probe/ca.crt"


def test_policy_monitor_forwards_postgres_tls(monkeypatch: pytest.MonkeyPatch) -> None:
    connect = MagicMock()
    monkeypatch.setattr("collector.core.policy_monitor.psycopg2.connect", connect)
    monitor = REGTECHPolicyMonitor(
        {
            "postgres_host": "blacklist-postgres",
            "postgres_sslrootcert": "/probe/ca.crt",
        }
    )

    monitor._get_db_connection()

    assert connect.call_args.kwargs["sslmode"] == "verify-full"
    assert connect.call_args.kwargs["sslrootcert"] == "/probe/ca.crt"


def test_collector_redis_params_require_verified_tls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(CollectorConfig, "INTERNAL_CA_CERT", "/probe/ca.crt")

    params = CollectorConfig.get_redis_connection_params()

    assert params["ssl"] is True
    assert params["ssl_cert_reqs"] == "required"
    assert params["ssl_ca_certs"] == "/probe/ca.crt"


def test_collector_redis_params_construct_a_supported_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(CollectorConfig, "INTERNAL_CA_CERT", "/probe/ca.crt")

    client = redis.Redis(**CollectorConfig.get_redis_connection_params())

    assert client.connection_pool.connection_class is redis.SSLConnection
    assert client.connection_pool.connection_kwargs["ssl_ca_certs"] == "/probe/ca.crt"
