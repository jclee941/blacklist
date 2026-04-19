# ============================================================================
# Blacklist Data Collector Service - Container Image
# ============================================================================
# Purpose: REGTECH automated data collection service
# Architecture: Multi-stage build (build deps separated from runtime)
# Dependencies: PostgreSQL 15, Redis 7, Python 3.11
# ============================================================================

# ---- Stage 1: Build (gcc, libpq-dev for C extensions) ----
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY collector/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# ---- Stage 2: Runtime (minimal) ----
FROM python:3.11-slim-bookworm

ARG APP_VERSION="0.0.0-dev"
ARG BUILD_DATE=""
ARG GIT_COMMIT="unknown"

LABEL org.opencontainers.image.version=${APP_VERSION}
LABEL org.opencontainers.image.revision=${GIT_COMMIT}
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.title="blacklist-collector"
LABEL org.opencontainers.image.description="Blacklist Data Collector Service"
LABEL maintainer="qws941"
LABEL com.docker.compose.project=blacklist
LABEL com.docker.compose.service=collector

WORKDIR /app

# Runtime-only system deps (no build tools, no Playwright browser libs)
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
        postgresql-client \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built Python packages from builder stage
COPY --from=builder /install /usr/local

# Upgrade pip/setuptools/wheel to patch CVEs from base image
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy collector source (flattened layout)
COPY collector/core/ /app/core/
COPY collector/utils/ /app/utils/
COPY collector/*.py /app/collector/
COPY collector/scheduler/ /app/collector/scheduler/

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Seoul \
    POSTGRES_HOST=blacklist-postgres \
    POSTGRES_PORT=5432 \
    POSTGRES_DB=blacklist \
    POSTGRES_USER=postgres \
    REDIS_HOST=blacklist-redis \
    REDIS_PORT=6379 \
    REGTECH_BASE_URL=https://regtech.fsec.or.kr \
    COLLECTOR_PORT=8545 \
    LOG_LEVEL=INFO

RUN mkdir -p /app/logs

EXPOSE 8545

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8545/health || exit 1

CMD ["python", "-m", "collector.run_collector"]
