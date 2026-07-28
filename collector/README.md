# Blacklist Collector

**Version:** `4.1.0`

The collector is an isolated Python 3.11 ETL service for scheduled and manual blacklist source collection. It must remain independent from `app/`; coordination happens through its service interfaces, shared data services, and HTTP, not Python imports from the Flask application.

## Responsibilities

- Collect and process REGTECH and configured source data.
- Schedule recurring collection work.
- Persist collection data through the collector database layer.
- Expose service health, status, logs, configuration, and manual collection controls on port `8545`.

## Key Files

| Path | Purpose |
| --- | --- |
| `run_collector.py` | Collector lifecycle entry point |
| `config.py` | Environment-backed collector configuration |
| `scheduler.py` | Collection scheduling and manual execution |
| `health_server.py` | Flask health and operational endpoints |
| `core/` | Source clients, processing, and database services |
| `api/` | Collector-facing API helpers |

## Configuration

The collector uses the PostgreSQL settings consumed by the Compose environment: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`. Other relevant settings include `COLLECTION_INTERVAL`, `HEALTH_CHECK_PORT`, `LOG_LEVEL`, and `DISABLE_AUTO_COLLECTION`.

Register source credentials through the supported application or collector credential flow. Don't commit credentials to environment files, examples, or documentation.

## Operational Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Health and collector summary |
| `GET /status` | Detailed collector status |
| `GET /logs` | Recent in-memory log records |
| `POST /trigger` | Start a supported source collection manually |
| `POST /api/test-auth/<source>` | Test configured source credentials |

## Run And Check

Use the root Compose commands for the supported runtime:

```bash
make dev
curl http://localhost:8545/health
curl http://localhost:8545/status
make test-collector-unit
```

The collector is covered by the changed-area jobs in `.github/workflows/ci.yml`; releases are prepared at the repository root with `scripts/release.sh`.
