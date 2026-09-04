# Blacklist

**Repository:** [jclee941/blacklist](https://github.com/jclee941/blacklist)
**Current version:** See [`VERSION`](VERSION), tracked in [CHANGELOG.md](CHANGELOG.md).

Blacklist is a containerized platform for collecting, managing, and distributing IP blacklist data. It combines a Flask API, an isolated collector service, a Next.js dashboard, PostgreSQL, and Redis.

## Services

| Service | Technology | Listener | Purpose |
| --- | --- | --- | --- |
| App | Flask, Python 3.11 | internal `2542` | REST API, blacklist management, Fortinet integration, settings, and monitoring |
| Frontend | Next.js 15, React 19 | container `3000`, host `443` | Dashboard and browser proxy for the Flask API |
| Collector | Python 3.11 | internal `8545` | Scheduled and manual blacklist source collection |
| PostgreSQL | PostgreSQL 15 | internal `5432` | Persistent data |
| Redis | Redis 7 | internal `6379` | Supporting cache and service state |

## Quick Start

Requirements: Docker and Docker Compose v2. Copy the development template to `deploy/.env`, populate its required secrets, and expose the local WARP proxy to `host.docker.internal:40000`. Internal TLS material defaults to `BLACKLIST_TLS_DIR=/etc/blacklist/tls`; a packaged installation provisions this directory automatically through `deploy/install.sh`.

```bash
cp deploy/.env.example deploy/.env
# Edit deploy/.env and set the required credentials and encryption secrets.
make dev
curl --fail --insecure https://localhost:443/health
```

The packaged frontend is the external endpoint on host port `443` and requires an operator-provided certificate matching `FRONTEND_TLS_SERVER_NAME`. Explicit `self-signed` mode is loopback-only for development. Flask, the collector, PostgreSQL, and Redis communicate over internal TLS using certificates from `BLACKLIST_TLS_DIR` (default `/etc/blacklist/tls`), listening on `2542`, `8545`, `5432`, and `6379`. For standalone frontend development, run `cd frontend && npm run dev`; it listens on `http://localhost:2543`.

## Architecture

1. The Next.js dashboard sends API requests through `frontend/lib/api.ts`.
2. `frontend/next.config.ts` proxies `/api`, health, metrics, static, and UI routes to Flask.
3. Flask handles blacklist, collection, Fortinet, settings, and monitoring APIs.
4. The collector runs independently, stores collection results through its service boundaries, and exposes health and status on port `8545`.
5. PostgreSQL persists application data and Redis supplies supporting state.

## Authentication

JWT token APIs are available at `/api/auth/login`, `/api/auth/me`, and `/api/auth/verify`. Dashboard and protected API routes require a valid administrator JWT by default; login, health, metrics, static assets, and explicitly public feeds remain open. Configure credentials and signing material with environment variables or the settings store. `DISABLE_JWT_AUTH=true` is reserved for explicit development use.

## Development

```bash
make help
make verify-lint
make test
cd frontend && npm run typecheck
```

See [frontend/README.md](frontend/README.md) for dashboard work and [collector/README.md](collector/README.md) for collector operation.

## CI And Releases

`.github/workflows/ci.yml` is the primary pull request and `master` CI workflow. It runs changed-area checks, builds images, scans images, and runs browser E2E tests.

Release from a clean `master` checkout with:

```bash
make release TYPE=patch
# or preview the release
make release-dry TYPE=minor
```

`scripts/release.sh` prepares the version, changelog, commit, and annotated tag. The tag triggers `.github/workflows/release.yml` to validate, package, publish GHCR images, and create the GitHub Release.

## Documentation

- [Application guide](AGENTS.md)
- [Documentation hub](docs/README.md)
- [GitHub workflow guide](.github/WORKFLOWS.md)
- [Change log](CHANGELOG.md)

Files in `docs/wiki/` and `docs/deliverables/` are historical records. They may describe earlier releases and aren't the source of current runtime, ownership, authentication, CI, or release behavior.
