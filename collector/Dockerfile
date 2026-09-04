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

# ---- Stage 2: Runtime (minimal) ----
FROM python:3.11-slim-bookworm

ARG APP_VERSION="0.0.0-dev"
ARG BUILD_DATE=""
ARG GIT_COMMIT="unknown"
ARG UID=10001
ARG GID=10001

ENV APP_VERSION=${APP_VERSION}

LABEL org.opencontainers.image.version=${APP_VERSION}
LABEL org.opencontainers.image.revision=${GIT_COMMIT}
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.title="blacklist-collector"
LABEL org.opencontainers.image.description="Blacklist Data Collector Service"
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
RUN rm -rf \
        /usr/local/lib/python3.11/site-packages/pip* \
        /usr/local/lib/python3.11/site-packages/setuptools* \
        /usr/local/lib/python3.11/site-packages/wheel* \
        /usr/local/lib/python3.11/site-packages/pkg_resources \
        /usr/local/lib/python3.11/site-packages/_distutils_hack \
        /usr/local/lib/python3.11/site-packages/distutils-precedence.pth \
    && rm -f /usr/local/bin/pip* /usr/local/bin/wheel


# Copy entire collector package preserving structure
COPY collector/ /app/collector/

ENV PYTHONPATH=/app:/app/collector \
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

RUN groupadd --gid "${GID}" collector \
    && useradd --uid "${UID}" --gid "${GID}" --no-create-home --shell /usr/sbin/nologin collector \
    && mkdir -p /app/data /app/logs \
    && chown -R collector:collector /app/data /app/logs

USER collector

EXPOSE 8545

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f --cacert /run/blacklist/ca.crt https://blacklist-collector:8545/health || exit 1

CMD ["python", "-m", "collector.run_collector"]
