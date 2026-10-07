# DEPLOY KNOWLEDGE BASE

## Overview

Compose inheritance for offline/air-gapped deployment. `base.yml` is the source of truth for all five services (postgres, redis, collector, app, frontend); `docker-compose.yml` and `docker-compose.release.yml` extend it for dev and prod.

## FILES

- `base.yml` - shared service definitions, internal TLS everywhere, source of truth.
- `docker-compose.yml` - dev overlay: extends base, adds build contexts, WARP proxy on by default.
- `docker-compose.release.yml` - production overlay: extends base, uses pre-built GHCR images; WARP follows the env file switch (off by default).
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

`WARP_ENABLED` is the switch and `WARP_PROXY_URL` only locates the proxy: `collector/core/regtech/collector.py` sends REGTECH session requests and curl downloads through the URL only while `WARP_ENABLED` is `true`/`1`/`yes`. `base.yml` passes both from the env file with defaults `false` and `http://host.docker.internal:40000` and maps `host.docker.internal` to the host gateway; the release overlay adds nothing, so the installed `/etc/blacklist/.env` decides. `install.sh` writes `WARP_ENABLED=false` on a fresh install, keeps the operator's values on every re-run, and rejects anything but `true`/`false` or a `SCHEME://HOST:PORT` URL (http, https, socks5, socks5h). `docker-compose.yml` defaults the switch on for development. Apply a change with `docker compose --env-file /etc/blacklist/.env -f docker-compose.yml up -d blacklist-collector` or by re-running `install.sh`. The proxy must listen on an address the Docker gateway reaches; a WARP proxy bound to `127.0.0.1` needs a relay, for example on `172.17.0.1:40000`.

## INSTALL FLOW (`install.sh`)

1. Check operator inputs before any mutation: the host release keyring or `--release-key` + `--fingerprint`, the frontend server name, and the certificate/key. Every missing item is reported at once.
2. Register a `--release-key` whose fingerprint matches (a different existing keyring is never replaced), then verify `MANIFEST.sha256` entries and its detached signature (`MANIFEST.sha256.asc`).
3. Install Docker/Compose if missing.
4. Verify image `checksums.sha256` immediately before loading images (`load_images`), load them, generate missing secrets (writing the initial admin password file right away when the password is generated), and provision internal TLS plus the frontend certificate/key and server name.
5. Start `blacklist-postgres` alone, wait for its health check, then run `configure-runtime-roles.sh` inside the container to bootstrap DB roles; its output is printed only on failure. A bundle built with `--seed-data` then imports `seed/blacklist_ips.csv.gz` into an empty `blacklist_ips` (never into a database that has rows), so the initial backfill is skipped.
6. Start the remaining services and wait for every container to report healthy.

## CONVENTIONS

- All services attach to the `blacklist-net` bridge and address peers by Compose service name.
- Health checks are mandatory on every service.
- Redis requires `REDIS_PASSWORD`, shared by its own health check plus the app and collector environments.
- `make build` requires a clean working tree; `VERSION` and tag consistency are enforced by the release pipeline.

## NOTES

- The app reaches collector control routes through `COLLECTOR_URL` (`app/core/config.py`, default `https://blacklist-collector:8545`).
- `install.sh` auto-generates `ADMIN_USERNAME=admin` and a random `ADMIN_PASSWORD` in `.env` on every fresh deployment and writes the initial password to a protected, operator-only file as soon as the secrets are generated, for import into a password manager; there is no separate manual fallback step. An operator may instead pre-create `/etc/blacklist/.env` with chosen values such as `ADMIN_PASSWORD` or `WARP_ENABLED`: when no deployment state exists, some required secret is missing or blank, and every set secret is a single literal, the installer keeps those values, generates only the missing or blank keys, rejects an `ADMIN_PASSWORD` outside the app's 12-character/72-byte policy before changing the file, and writes the initial password file only for a generated password. On an existing deployment a partial env file is still rejected.
- Optional `REGTECH_ID`/`REGTECH_PW` in the env file reach only the app, which stores them once (encrypted, through `secure_credential_service`) when `collection_credentials` has no REGTECH row; the collector still reads only `collector_regtech_credentials`, and dashboard edits are never overwritten. `install.sh` requires both or neither and rejects unresolved values. With them, a fresh install starts the initial 90-day backfill without a dashboard step.
- `install.sh --export-seed-data FILE` dumps `blacklist_ips` from a running installation as gzip CSV (fixed column list `SEED_DATA_COLUMNS`) for `scripts/build_offline_bundle.py --seed-data FILE`; both export and import go through `psql` inside `blacklist-postgres` over its TLS listener. The rebuilt `MANIFEST.sha256` invalidates the release signature, so a data bundle needs a new `MANIFEST.sha256.asc` from a key the target host registers; a host that already trusts another key rejects it.
- `ADMIN_PASSWORD` only bootstraps the administrator row: once the app writes the bcrypt hash, the DB is authoritative and the env value is never reactivated. It stays readable in `.env` and through `docker inspect`, so the installer instructs the operator to rotate the password in the dashboard and overwrite the `.env` value afterwards.
