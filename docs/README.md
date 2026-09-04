# Blacklist Documentation

**Repository:** [jclee941/blacklist](https://github.com/jclee941/blacklist)
**Current version:** `5.0.0`

This is the documentation entry point for the current Blacklist application. The current system consists of a Flask API, an independent Python collector, a Next.js dashboard, PostgreSQL, Redis, Docker Compose deployment, and GitHub Actions automation.

## Current References

| Need                                      | Current source                                      |
| ----------------------------------------- | --------------------------------------------------- |
| Application architecture and change rules | [Root AGENTS.md](../AGENTS.md)                      |
| Local operation and service overview      | [Root README.md](../README.md)                      |
| Dashboard development                     | [Frontend README](../frontend/README.md)            |
| Collector operation                       | [Collector README](../collector/README.md)          |
| CI and release workflow                   | [GitHub workflow guide](../.github/WORKFLOWS.md)    |
| Version and release history               | [VERSION](../VERSION), [CHANGELOG](../CHANGELOG.md) |

## Current Runtime Facts

| Service          | Role                               | Default port |
| ---------------- | ---------------------------------- | ------------ |
| Flask app        | REST APIs and application services | `2542`       |
| Next.js frontend | Dashboard and Flask proxy          | `2543`       |
| Collector        | Source collection and health API   | `8545`       |
| PostgreSQL       | Persistent storage                 | `5432`       |
| Redis            | Supporting state                   | `6379`       |

JWT token APIs and global JWT enforcement protect dashboard and application APIs by default. Login, health, metrics, and static assets remain unauthenticated. `@public` Fortinet feeds skip the administrator JWT but apply `feed_access_required` bearer-token and source-network checks. See `app/core/routes/api/auth_routes.py`, `app/core/auth/middleware.py`, and `app/core/auth/feed.py` before changing authentication documentation.

## CI And Releases

`ci.yml` is the primary pull request and `master` CI workflow. The supported release entry point is `scripts/release.sh`, available through `make release` and `make release-dry`. Release tags trigger `release.yml`, which validates the version and changelog, builds images, packages the release, creates a GitHub Release, and publishes GHCR images.

## Historical Records

`wiki/` and `deliverables/` preserve earlier operational material and project deliverables. They are historical records and may describe older versions, architecture, endpoints, ownership, or release practices. Do not treat them as current-state documentation without reconciling them with the sources above.

| Historical collection    | Entry point                                        |
| ------------------------ | -------------------------------------------------- |
| Operations wiki          | [wiki/Home.md](wiki/Home.md)                       |
| Project deliverables     | [deliverables/index.md](deliverables/index.md)     |
| Previous migration notes | [CLOUDFLARE_MIGRATION.md](CLOUDFLARE_MIGRATION.md) |
