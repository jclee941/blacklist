from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parents[2]
BASE_SOURCE = (ROOT / "deploy" / "base.yml").read_text(encoding="utf-8")
POSTGRES_DOCKERFILE = (ROOT / "postgres" / "Dockerfile").read_text(encoding="utf-8")
POSTGRES_TLS_ENTRYPOINT = ROOT / "postgres" / "tls-entrypoint.sh"
POSTGRES_TLS_CONFIG = ROOT / "postgres" / "configure-tls.sh"
REDIS_DOCKERFILE = (ROOT / "deploy" / "redis" / "Dockerfile").read_text(encoding="utf-8")
APP_RUN_SOURCE = (ROOT / "app" / "run_app.py").read_text(encoding="utf-8")
FRONTEND_TLS_PRELOAD = ROOT / "deploy" / "frontend-internal-tls.cjs"


def service_block(service_name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(service_name)}:\n.*?(?=^(?:\S|  \S)|\Z)",
        BASE_SOURCE,
    )
    assert match is not None, f"service block not found: {service_name}"
    return match.group(0)


def test_postgres_server_requires_tls() -> None:
    postgres = service_block("blacklist-postgres")

    assert "ssl=on" in postgres
    assert "ssl_cert_file=/run/blacklist/tls/tls.crt" in postgres
    assert "ssl_key_file=/run/blacklist/tls/tls.key" in postgres
    assert "ssl_min_protocol_version=TLSv1.2" in postgres
    assert "${BLACKLIST_TLS_DIR:-/etc/blacklist/tls}/postgres:/run/blacklist/tls:ro" in postgres


def test_postgres_healthcheck_verifies_the_server_certificate() -> None:
    postgres = service_block("blacklist-postgres")

    assert "PGSSLMODE=verify-full" in postgres
    assert "PGSSLROOTCERT=/run/blacklist/ca.crt" in postgres
    assert "psql -h blacklist-postgres" in postgres
    assert "pg_isready" not in postgres


def test_postgres_rejects_plaintext_on_fresh_and_existing_databases() -> None:
    assert POSTGRES_TLS_ENTRYPOINT.is_file()
    assert POSTGRES_TLS_CONFIG.is_file()

    entrypoint = POSTGRES_TLS_ENTRYPOINT.read_text(encoding="utf-8")
    tls_config = POSTGRES_TLS_CONFIG.read_text(encoding="utf-8")
    assert "configure-postgres-tls" in entrypoint
    assert "hostssl all all 0.0.0.0/0 md5" in tls_config
    assert "hostnossl all all 0.0.0.0/0 reject" in tls_config
    assert "hostssl all all ::/0 md5" in tls_config
    assert "hostnossl all all ::/0 reject" in tls_config
    assert "ENTRYPOINT [\"tls-entrypoint.sh\"]" in POSTGRES_DOCKERFILE
    assert "/docker-entrypoint-initdb.d/00-configure-tls.sh" in POSTGRES_DOCKERFILE


def test_redis_server_exposes_only_tls() -> None:
    redis = service_block("blacklist-redis")

    assert "--port" in redis
    assert re.search(r"(?m)^      - ['\"]?0['\"]?$", redis)
    assert "--tls-port" in redis
    assert re.search(r"(?m)^      - ['\"]?6379['\"]?$", redis)
    assert "--tls-cert-file" in redis
    assert "/run/blacklist/tls/tls.crt" in redis
    assert "--tls-key-file" in redis
    assert "/run/blacklist/tls/tls.key" in redis
    assert "--tls-ca-cert-file" in redis
    assert "/run/blacklist/ca.crt" in redis
    assert "--tls-auth-clients" in redis
    assert "${BLACKLIST_TLS_DIR:-/etc/blacklist/tls}/redis:/run/blacklist/tls:ro" in redis


def test_redis_healthcheck_verifies_the_server_certificate() -> None:
    redis = service_block("blacklist-redis")

    assert "redis-cli --tls" in redis
    assert "--cacert /run/blacklist/ca.crt" in redis
    assert "-h blacklist-redis" in redis
    assert "REDISCLI_AUTH=" in redis
    assert "redis-cli ping" not in REDIS_DOCKERFILE


def test_collector_clients_receive_the_internal_ca() -> None:
    collector = service_block("blacklist-collector")

    assert "INTERNAL_CA_CERT: /run/blacklist/ca.crt" in collector
    assert (
        "${BLACKLIST_TLS_DIR:-/etc/blacklist/tls}/ca/ca.crt:/run/blacklist/ca.crt:ro"
        in collector
    )


def test_app_and_collector_serve_https_with_target_certificates() -> None:
    app = service_block("blacklist-app")
    collector = service_block("blacklist-collector")

    assert "SSL_ENABLED" not in app
    assert "INTERNAL_TLS_CERT: /run/blacklist/tls/tls.crt" in app
    assert "INTERNAL_TLS_KEY: /run/blacklist/tls/tls.key" in app
    assert "${BLACKLIST_TLS_DIR:-/etc/blacklist/tls}/app:/run/blacklist/tls:ro" in app
    assert "https://blacklist-app:2542/health" in app
    assert "INTERNAL_TLS_CERT: /run/blacklist/tls/tls.crt" in collector
    assert "INTERNAL_TLS_KEY: /run/blacklist/tls/tls.key" in collector
    assert "${BLACKLIST_TLS_DIR:-/etc/blacklist/tls}/collector:/run/blacklist/tls:ro" in collector
    assert "https://blacklist-collector:8545/health" in collector
    assert "ssl_context=" in APP_RUN_SOURCE


def test_internal_service_urls_use_https_and_frontend_verifies_the_ca() -> None:
    app = service_block("blacklist-app")
    collector = service_block("blacklist-collector")
    frontend = service_block("blacklist-frontend")

    assert "COLLECTOR_URL: https://blacklist-collector:8545" in app
    assert "BLACKLIST_API_URL: https://blacklist-app:2542/api" in app
    assert "BLACKLIST_API_URL: https://blacklist-app:2542" in collector
    assert "NEXT_PUBLIC_API_URL: https://blacklist-app:2542" in frontend
    assert "NODE_OPTIONS: --require=/run/blacklist/frontend-internal-tls.cjs" in frontend
    assert "/run/blacklist/ca.crt:ro" in frontend
    assert "/run/blacklist/frontend-internal-tls.cjs:ro" in frontend
    assert "http://blacklist-app" not in BASE_SOURCE
    assert "http://blacklist-collector" not in BASE_SOURCE

    assert FRONTEND_TLS_PRELOAD.is_file()
    preload = FRONTEND_TLS_PRELOAD.read_text(encoding="utf-8")
    assert "https.request" in preload
    assert "ca:" in preload
