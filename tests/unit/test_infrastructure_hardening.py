from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parents[2]
BASE = (ROOT / "deploy" / "base.yml").read_text(encoding="utf-8")


def _service_block(service_name: str) -> str:
    match = re.search(rf"(?ms)^  {re.escape(service_name)}:\n.*?(?=^(?:\S|  \S)|\Z)", BASE)
    assert match is not None
    return match.group(0)


def test_services_apply_compatible_container_hardening() -> None:
    # Given: every long-running service in the base Compose definition.
    for service in ("blacklist-app", "blacklist-collector", "blacklist-postgres", "blacklist-redis", "blacklist-frontend"):
        block = _service_block(service)

        # When/Then: privilege escalation, ambient capabilities, PID exhaustion, and unbounded memory are constrained.
        assert "no-new-privileges:true" in block, service
        assert re.search(r"(?m)^    cap_drop:\n      - ALL$", block), service
        assert re.search(r"(?m)^    pids_limit: [1-9][0-9]*$", block), service
        assert re.search(r"(?m)^    mem_limit: [1-9]", block), service


def test_collector_image_runs_as_fixed_non_root_user_with_writable_paths() -> None:
    # Given: the collector runtime image definition.
    source = (ROOT / "collector" / "Dockerfile").read_text(encoding="utf-8")

    # When/Then: its persistent write paths belong to a fixed unprivileged identity.
    assert "UID=10001" in source
    assert "GID=10001" in source
    assert "/app/data" in source and "/app/logs" in source
    assert "chown" in source
    assert re.search(r"(?m)^USER (?:collector|10001)$", source)


def test_fortigate_connections_never_disable_peer_verification() -> None:
    # Given: all FortiGate HTTPS and SSH adapters.
    paths = (
        ROOT / "collector" / "core" / "fortigate" / "collector.py",
        ROOT / "collector" / "core" / "fortigate" / "ssh_client.py",
        ROOT / "app" / "core" / "routes" / "api" / "fortinet" / "management.py",
        ROOT / "app" / "core" / "routes" / "api" / "fortinet_register.py",
    )
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    # When/Then: certificate and host-key verification cannot be bypassed.
    assert "verify=False" not in source
    assert "AutoAddPolicy" not in source
    assert "FORTIGATE_CA_CERT" in source
    assert "FORTIGATE_SSH_KNOWN_HOSTS" in source


def test_compose_passes_security_and_trust_boundaries_explicitly() -> None:
    # Given: the app and collector deployment environments.
    app = _service_block("blacklist-app")
    collector = _service_block("blacklist-collector")

    # When/Then: auth, proxy, public-feed, and FortiGate trust policy are explicit inputs.
    for setting in ("JWT_SECRET_KEY", "TRUSTED_PROXY_NETWORKS", "FORTINET_FEED_TOKEN", "FORTIGATE_ALLOWED_NETWORKS", "FORTIGATE_CA_CERT", "FORTIGATE_SSH_KNOWN_HOSTS"):
        assert setting in app, setting
    for setting in ("COLLECTOR_AUTH_TOKEN", "WARP_PROXY_URL", "FORTIGATE_CA_CERT", "FORTIGATE_SSH_KNOWN_HOSTS"):
        assert setting in collector, setting


def test_deployment_uses_distinct_cryptographic_keys_and_trusts_only_the_frontend_hop() -> None:
    app = _service_block("blacklist-app")
    installer = (ROOT / "deploy" / "install.sh").read_text(encoding="utf-8")

    assert "FLASK_SECRET_KEY: ${FLASK_SECRET_KEY:?FLASK_SECRET_KEY is required}" in app
    assert "JWT_SECRET_KEY: ${JWT_SECRET_KEY:?JWT_SECRET_KEY is required}" in app
    assert "SETTINGS_ENCRYPTION_KEY: ${SETTINGS_ENCRYPTION_KEY:?SETTINGS_ENCRYPTION_KEY is required}" in app
    assert "TRUSTED_PROXY_NETWORKS: ${TRUSTED_PROXY_NETWORKS:-172.30.0.10/32}" in app
    assert "FLASK_SECRET_KEY=${flask_secret_key}" in installer
    assert "JWT_SECRET_KEY=${jwt_secret_key}" in installer
    assert "SETTINGS_ENCRYPTION_KEY=${settings_encryption_key}" in installer


def test_production_crypto_configuration_has_no_random_or_static_fallback() -> None:
    # Given: application and settings-service cryptographic bootstrap code.
    app_source = (ROOT / "app" / "core" / "app.py").read_text(encoding="utf-8")
    settings_source = (ROOT / "app" / "core" / "services" / "settings_service.py").read_text(encoding="utf-8")

    # When/Then: production startup requires explicit stable keys.
    assert "process-local" not in app_source
    assert "blacklist-secret-key-change-in-production" not in settings_source
    assert "SETTINGS_ENCRYPTION_KEY" in settings_source


def test_legacy_plaintext_credential_service_is_not_registered() -> None:
    factory = (ROOT / "app" / "core" / "services" / "service_factory.py").read_text(encoding="utf-8")

    assert 'services["credential_service"]' not in factory
    assert 'services["secure_credential_service"]' in factory


def test_frontend_tls_policy_is_explicit_and_persistent() -> None:
    # Given: the frontend runtime policy and Compose storage contract.
    entrypoint = (ROOT / "frontend" / "entrypoint.sh").read_text(encoding="utf-8")
    frontend = _service_block("blacklist-frontend")

    # When/Then: provided certificates fail closed and deliberate self-signed certificates survive restarts.
    assert 'TLS_MODE="${FRONTEND_TLS_MODE:-}"' in entrypoint
    assert 'TLS_MODE" = "provided"' in entrypoint
    assert 'TLS_MODE" = "self-signed"' in entrypoint
    assert "BLACKLIST_FRONTEND_TLS_DIR" in frontend
    assert ":/app/ssl" in frontend
    assert "FRONTEND_BIND_ADDRESS" in frontend
    assert "subjectAltName=DNS:localhost,IP:127.0.0.1" in entrypoint
    assert 'openssl x509 -in "$SSL_CERT" -noout -ext subjectAltName' in entrypoint
    assert 'rm -f "$SSL_KEY" "$SSL_CERT"' not in entrypoint


def test_production_images_use_production_wsgi_and_lock_only_installation() -> None:
    # Given: Python and Node production dependency/install definitions.
    app_entrypoint = (ROOT / "app" / "entrypoint.sh").read_text(encoding="utf-8")
    collector_dockerfile = (ROOT / "collector" / "Dockerfile").read_text(encoding="utf-8")
    app_requirements = (ROOT / "app" / "requirements.txt").read_text(encoding="utf-8")
    collector_requirements = (ROOT / "collector" / "requirements.txt").read_text(encoding="utf-8")
    frontend_dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")

    # When/Then: production does not use Werkzeug and frontend never falls back to lockfile-mutating install.
    assert "gunicorn==" in app_requirements
    assert "cheroot==" in collector_requirements
    assert "gunicorn" in app_entrypoint
    assert "--no-control-socket" in app_entrypoint
    assert "collector.run_collector" in collector_dockerfile
    assert "npm install" not in frontend_dockerfile
    assert all(
        package not in app_requirements
        for package in ("pytest==", "pytest-cov==", "pytest-mock==", "black==", "flake8==")
    )


def test_python_runtime_images_remove_packaging_toolchains() -> None:
    app_dockerfile = (ROOT / "app" / "Dockerfile").read_text(encoding="utf-8")
    collector_dockerfile = (ROOT / "collector" / "Dockerfile").read_text(encoding="utf-8")

    for dockerfile in (app_dockerfile, collector_dockerfile):
        assert "/usr/local/bin/pip*" in dockerfile
        assert "site-packages/distutils-precedence.pth" in dockerfile
        assert "site-packages/setuptools*" in dockerfile
        assert "site-packages/wheel*" in dockerfile


def test_runtime_images_export_the_build_version() -> None:
    dockerfiles = (
        ROOT / "app/Dockerfile",
        ROOT / "collector/Dockerfile",
        ROOT / "frontend/Dockerfile",
        ROOT / "postgres/Dockerfile",
        ROOT / "deploy/redis/Dockerfile",
    )

    for dockerfile in dockerfiles:
        assert "ENV APP_VERSION=${APP_VERSION}" in dockerfile.read_text(encoding="utf-8")


def test_postgres_replaces_vulnerable_gosu_runtime() -> None:
    dockerfile = (ROOT / "postgres" / "Dockerfile").read_text(encoding="utf-8")

    assert "apk upgrade --no-cache" in dockerfile
    assert "apk add --no-cache su-exec" in dockerfile
    assert "rm -f /usr/local/bin/gosu" in dockerfile


def test_postgres_keeps_bootstrap_owner_and_creates_separate_runtime_roles() -> None:
    compose = (ROOT / "deploy/base.yml").read_text(encoding="utf-8")
    role_script = (ROOT / "postgres/configure-runtime-roles.sh").read_text(encoding="utf-8")

    assert "APP_DB_USER" in compose
    assert "COLLECTOR_DB_USER" in compose
    assert "NOBYPASSRLS" in role_script
    assert "GRANT USAGE, CREATE ON SCHEMA public" in role_script
    assert "GRANT SELECT, INSERT, UPDATE, DELETE" in role_script


def test_frontend_runner_contains_custom_server_dependencies() -> None:
    frontend_dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY --from=builder /app/server-routing.js ./server-routing.js" in frontend_dockerfile


def test_frontend_dockerfile_uses_entrypoint_tls_path_defaults() -> None:
    dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    entrypoint = (ROOT / "frontend" / "entrypoint.sh").read_text(encoding="utf-8")

    assert "ENV SSL_KEY_PATH" not in dockerfile
    assert "ENV SSL_CERT_PATH" not in dockerfile
    assert 'SSL_KEY="${SSL_KEY_PATH:-$SSL_DIR/server.key}"' in entrypoint
    assert 'SSL_CERT="${SSL_CERT_PATH:-$SSL_DIR/server.crt}"' in entrypoint


def test_frontend_custom_server_uses_standard_url_parsing() -> None:
    server = (ROOT / "frontend" / "server.js").read_text(encoding="utf-8")

    assert "require('url')" not in server


def test_collector_file_and_collection_limits_are_configured() -> None:
    # Given: collector configuration and bounded I/O entry points.
    config = (ROOT / "collector" / "config.py").read_text(encoding="utf-8")
    archive = (ROOT / "collector" / "core" / "archive_manager.py").read_text(encoding="utf-8")
    manual = (ROOT / "collector" / "scheduler" / "manual.py").read_text(encoding="utf-8")
    logging_source = (ROOT / "collector" / "run_collector.py").read_text(encoding="utf-8")
    excel = (ROOT / "collector" / "core" / "regtech_excel.py").read_text(encoding="utf-8")

    # When/Then: every previously unbounded disk/page path has a hard limit or safe temporary file primitive.
    for setting in ("MAX_PAGES_PER_COLLECTION", "MAX_ARCHIVE_BYTES", "ARCHIVE_RETENTION_DAYS", "LOG_MAX_BYTES", "LOG_BACKUP_COUNT"):
        assert setting in config
    assert "MAX_ARCHIVE_BYTES" in archive and "ARCHIVE_RETENTION_DAYS" in archive
    assert "max_pages=CollectorConfig.MAX_PAGES_PER_COLLECTION" in manual
    assert "RotatingFileHandler" in logging_source
    assert "/tmp/regtech_data.xlsx" not in excel
    assert "NamedTemporaryFile" in excel
    assert '"/usr/bin/curl"' in excel


def test_installer_volume_migration_has_minimal_privileges() -> None:
    installer = (ROOT / "deploy" / "install.sh").read_text(encoding="utf-8")

    assert "--cap-drop ALL" in installer
    assert "--cap-add CHOWN" in installer
    assert "--network none" in installer
    assert "--read-only" in installer


def test_internal_tls_preload_covers_request_and_get() -> None:
    preload = (ROOT / "deploy" / "frontend-internal-tls.cjs").read_text(encoding="utf-8")

    assert "http.request =" in preload
    assert "http.get =" in preload


def test_compose_assigns_a_single_trusted_frontend_address() -> None:
    development = (ROOT / "deploy" / "docker-compose.yml").read_text(encoding="utf-8")
    release = (ROOT / "deploy" / "docker-compose.release.yml").read_text(encoding="utf-8")

    for compose in (development, release):
        assert "subnet: ${BLACKLIST_NETWORK_SUBNET:-172.30.0.0/24}" in compose
    assert "ipv4_address: ${FRONTEND_INTERNAL_IP:-172.30.0.10}" in BASE
