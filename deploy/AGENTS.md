# DEPLOY KNOWLEDGE BASE

## Overview

Compose inheritance for offline/air-gapped deployment. `base.yml` is the source of truth for all five services (postgres, redis, collector, app, frontend); `docker-compose.yml` and `docker-compose.release.yml` extend it for dev and prod.

## FILES

- `base.yml` - shared service definitions, internal TLS everywhere, source of truth.
- `docker-compose.yml` - dev overlay: extends base, adds build contexts, WARP proxy on by default.
- `docker-compose.release.yml` - production overlay: extends base, uses pre-built GHCR images, WARP forced off.
- `install.sh` - offline installer: bundle/image integrity checks, Docker install, TLS provisioning, secrets, PostgreSQL bootstrap, health checks.
- `init-secrets.sh` (legacy, unused) - would generate `CREDENTIAL_MASTER_KEY`/`SECRET_KEY`/`CREDENTIAL_ENCRYPTION_KEY` on first boot into a shared volume; `collector/entrypoint.sh` still sources it if present, but `collector/Dockerfile` never copies it in and its `CMD` bypasses `entrypoint.sh` entirely. `install.sh` now generates every secret directly into `.env` before containers start.
- `.env.example` - required secrets template.
- `redis/Dockerfile` - builds the TLS-only Redis image (see Redis below).
- `prereqs/docker.service` - systemd unit for offline Docker installs.

## NETWORK AND TLS

Only `blacklist-frontend` publishes a host port (`443` -> container `3000`). Postgres, Redis, the collector, and the app publish nothing; every service talks over the `blacklist-net` bridge using certificates under `BLACKLIST_TLS_DIR` (default `/etc/blacklist/tls`).

- Frontend: `FRONTEND_TLS_MODE=provided` requires an operator certificate/key at `FRONTEND_TLS_DIR` matching `FRONTEND_TLS_SERVER_NAME`; `install.sh` checks expiry, hostname match, and that the key matches the cert. `--server-name`, `--tls-cert`, and `--tls-key` install them. Hostname coverage is judged from openssl's verdict text because `x509 -checkhost`/`-checkip` exit 0 on a mismatch. `self-signed` mode is loopback-only and for development.
- Internal traffic (Postgres, Redis, collector, app): install-generated CA. Postgres uses `sslmode=verify-full`; Redis is TLS-only (`tls-auth-clients no`, plaintext port disabled).

## WARP

`WARP_ENABLED` is a compose-level posture flag only — collector code never reads it. The actual outbound-proxy switch is `WARP_PROXY_URL`: `collector/core/regtech/collector.py` proxies REGTECH traffic whenever that value is nonempty. Development-only in practice: `docker-compose.yml` defaults both to a host proxy at `host.docker.internal:40000`; `base.yml`, `docker-compose.release.yml`, and `install.sh` set both to disabled/empty for release and the installed bundle.

## INSTALL FLOW (`install.sh`)

1. Check operator inputs before any mutation: the host release keyring or `--release-key` + `--fingerprint`, the frontend server name, and the certificate/key. Every missing item is reported at once.
2. Register a `--release-key` whose fingerprint matches (a different existing keyring is never replaced), then verify `MANIFEST.sha256` entries and its detached signature (`MANIFEST.sha256.asc`).
3. Install Docker/Compose if missing.
4. Verify image `checksums.sha256` immediately before loading images (`load_images`), load them, generate secrets (writing the initial admin password file right away), and provision internal TLS plus the frontend certificate/key and server name.
5. Start `blacklist-postgres` alone, wait for its health check, then run `configure-runtime-roles.sh` inside the container to bootstrap DB roles; its output is printed only on failure.
6. Start the remaining services and wait for every container to report healthy.

## CONVENTIONS

- All services attach to the `blacklist-net` bridge and address peers by Compose service name.
- Health checks are mandatory on every service.
- Redis requires `REDIS_PASSWORD`, shared by its own health check plus the app and collector environments.
- `make build` requires a clean working tree; `VERSION` and tag consistency are enforced by the release pipeline.

## NOTES

- The app reaches collector control routes through `COLLECTOR_URL` (`app/core/config.py`, default `https://blacklist-collector:8545`).
- `install.sh` auto-generates `ADMIN_USERNAME=admin` and a random `ADMIN_PASSWORD` in `.env` on every fresh deployment and writes the initial password to a protected, operator-only file as soon as the secrets are generated, for import into a password manager; there is no separate manual fallback step.
- `ADMIN_PASSWORD` only bootstraps the administrator row: once the app writes the bcrypt hash, the DB is authoritative and the env value is never reactivated. It stays readable in `.env` and through `docker inspect`, so the installer instructs the operator to rotate the password in the dashboard and overwrite the `.env` value afterwards.
