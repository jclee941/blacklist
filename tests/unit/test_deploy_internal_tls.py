from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parents[2]
BASE_SOURCE = (ROOT / "deploy" / "base.yml").read_text(encoding="utf-8")
POSTGRES_DOCKERFILE = (ROOT / "postgres" / "Dockerfile").read_text(encoding="utf-8")
POSTGRES_TLS_ENTRYPOINT = ROOT / "postgres" / "tls-entrypoint.sh"
POSTGRES_TLS_CONFIG = ROOT / "postgres" / "configure-tls.sh"


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
