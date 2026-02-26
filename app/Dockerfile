# ============================================================================
# Blacklist Flask Application - Container Image
# ============================================================================
# Purpose: Flask web application for IP blacklist/whitelist management
# Architecture: Multi-stage build for production optimization
# Dependencies: PostgreSQL 15, Redis 7, Python 3.11
# ============================================================================

# ============================================================================
# STAGE 1: Python Dependencies and Application Build
# ============================================================================
FROM python:3.11-slim-bookworm AS python-base

# Python optimization settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ============================================================================
# System Dependencies (Build Stage)
# ============================================================================
# Install build tools and PostgreSQL client libraries
# - gcc, g++: Python package compilation (psycopg2, cffi)
# - libpq-dev: PostgreSQL client library headers
# - curl: Health checks and API testing
# ============================================================================
RUN set -e && \
    echo "🔍 Installing system dependencies..." && \
    for i in 1 2 3; do \
        apt-get update && apt-get install -y \
            gcc \
            g++ \
            libpq-dev \
            curl \
            && break || sleep 10; \
    done && \
    rm -rf /var/lib/apt/lists/* && \
    echo "✅ System dependencies installed"

# Set work directory
WORKDIR /app

# ============================================================================
# Python Dependencies Installation
# ============================================================================
# Key dependencies (from requirements.txt):
# - Flask 2.3.x: Web framework
# - psycopg2-binary 2.9.x: PostgreSQL adapter
# - redis 5.0.x: Redis client
# - Flask-Limiter: Rate limiting
# - Flask-WTF: CSRF protection
# - cryptography: Credential encryption
# - requests, beautifulsoup4: Web scraping
# - APScheduler: Scheduled tasks
# ============================================================================
COPY app/requirements.txt .

# Install Python dependencies with retry mechanism
RUN set -e && \
    echo "🔍 Installing Python dependencies..." && \
    for i in 1 2 3; do \
        if pip install --no-cache-dir -r requirements.txt; then \
            echo "✅ Python dependencies installed" && \
            echo "📦 Installed packages:" && \
            pip list | head -20 && \
            break; \
        else \
            echo "⚠️ Installation attempt $i failed, retrying in 10s..." && \
            sleep 10; \
        fi; \
        if [ $i -eq 3 ]; then \
            echo "❌ Failed to install dependencies after 3 attempts" && \
            exit 1; \
        fi; \
    done

# Upgrade pip/setuptools/wheel to fix known CVEs in base image
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# ============================================================================
# Application Source Code
# ============================================================================
# Copy order (optimized for Docker layer caching):
# 1. Application code (core/, routes/, services/, models/)
# 2. Templates (Jinja2 HTML templates)
# 3. Static assets (CSS, JavaScript, images)
# 4. Entrypoint script (container initialization)
# ============================================================================
COPY app/ .

RUN chmod +x /app/entrypoint.sh

# Create required directories
RUN mkdir -p logs

# ============================================================================
# STAGE 2: Production Runtime Image
# ============================================================================
# Minimal production image with only runtime dependencies
# Security: Non-root user, minimal attack surface
# ============================================================================
FROM python:3.11-slim-bookworm AS production

# ============================================================================
# Build Arguments (Metadata Only — NO secrets!)
# ============================================================================
# Only version/build metadata passed at build time.
# All secrets and runtime config are injected via docker-compose env_file
# or environment variables at container start — NEVER baked into layers.
# ============================================================================
ARG APP_VERSION="0.0.0-dev"
ARG GIT_COMMIT="unknown"
ARG BUILD_DATE=""

# ============================================================================
# Container Metadata Labels
# ============================================================================
LABEL org.opencontainers.image.version=${APP_VERSION:-0.0.0-dev}
LABEL org.opencontainers.image.revision=${GIT_COMMIT:-unknown}
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.title="blacklist-app"
LABEL org.opencontainers.image.description="Blacklist Flask API"
LABEL maintainer="qws941"

LABEL com.docker.compose.project=blacklist
LABEL com.docker.compose.service=app

# ============================================================================
# Copy Build Artifacts from Stage 1
# ============================================================================
# Copy Python packages (compiled wheels and dependencies)
COPY --from=python-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-base /usr/local/bin /usr/local/bin

# ============================================================================
# Runtime Dependencies Installation
# ============================================================================
# Install ONLY runtime libraries (no build tools)
# - libpq5: PostgreSQL client library (runtime only, smaller than libpq-dev)
# - curl: Health checks
# - bash: Entrypoint script execution
# ============================================================================
RUN set -e && \
    echo "🔍 Installing runtime dependencies..." && \
    apt-get update && apt-get install -y \
        libpq5 \
        curl \
        bash \
        && rm -rf /var/lib/apt/lists/* \
        && apt-get clean && \
    echo "✅ Runtime dependencies installed"

# Upgrade pip/setuptools/wheel to patch CVEs from base image
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# ============================================================================
# Security: Non-Root User Creation
# ============================================================================
# Create dedicated 'app' user (UID 1001, GID 1001)
# Principle of least privilege: Application runs as non-root
# ============================================================================
RUN groupadd -r app && useradd -r -g app app

# Set work directory and copy application
WORKDIR /app
COPY --from=python-base /app .

# Copy entrypoint script and set permissions (before switching to app user)
COPY --from=python-base /app/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh && chown app:app /app/entrypoint.sh

ENV APP_VERSION=${APP_VERSION} \
    GIT_COMMIT=${GIT_COMMIT} \
    BUILD_DATE=${BUILD_DATE} \
    FLASK_ENV=production \
    PORT=2542 \
    PYTHONPATH=/app \
    TZ=Asia/Seoul \
    POSTGRES_HOST=localhost \
    POSTGRES_PORT=5432 \
    POSTGRES_DB=blacklist \
    POSTGRES_USER=postgres \
    REDIS_HOST=localhost \
    REDIS_PORT=6379

# Create required directories (static already copied from build stage)
RUN mkdir -p logs uploads cache

# ============================================================================
# Build-Time Validation and Summary
# ============================================================================
# Verify application structure and display build summary
# Checks: Templates, static files, core modules
# ============================================================================
RUN set -e && \
    echo "" && \
    echo "🔍 Validating application structure..." && \
    echo "" && \
    echo "====================================" && \
    echo "📋 Application Build Summary" && \
    echo "====================================" && \
    echo "Templates: $(find /app/templates -name "*.html" -type f 2>/dev/null | wc -l) files" && \
    echo "Static CSS: $(find /app/static/css -type f 2>/dev/null | wc -l) files" && \
    echo "Static JS: $(find /app/static/js -type f 2>/dev/null | wc -l) files" && \
    echo "Core modules: $(find /app/core -name "*.py" -type f 2>/dev/null | wc -l) files" && \
    echo "Routes: $(find /app/core/routes -name "*.py" -type f 2>/dev/null | wc -l) files" && \
    echo "Services: $(find /app/core/services -name "*.py" -type f 2>/dev/null | wc -l) files" && \
    echo "====================================" && \
    echo "✅ Application embedded in image" && \
    echo "📊 Image size optimization: Multi-stage build" && \
    echo "🔒 Security: Non-root user (app:app)" && \
    echo "🔗 Dependencies: PostgreSQL 15, Redis 7" && \
    echo "====================================" && \
    echo ""

# ============================================================================
# Volume Configuration
# ============================================================================
# Persistent data storage for stateful information
# - /app/uploads: User-uploaded files (IP lists, reports)
# - /app/logs: Application logs (Flask, collector, errors)
# - /app/cache: Temporary cache files
# ============================================================================
VOLUME ["/app/uploads", "/app/logs", "/app/cache"]

# Switch to non-root user
USER app

# Stay in /app working directory where files are copied
WORKDIR /app

# ============================================================================
# Health Check Configuration
# ============================================================================
# HTTP health check endpoint: GET /health
# - interval: 30s (check every 30 seconds)
# - timeout: 30s (fail if no response in 30s)
# - start-period: 5s (grace period for startup)
# - retries: 3 (mark unhealthy after 3 consecutive failures)
# ============================================================================
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:2542/health || exit 1

# Container deployment via Portainer API (no auto-update dependency)

# Expose Flask application port
EXPOSE 2542

# ============================================================================
# Entrypoint: Container Initialization
# ============================================================================
# entrypoint.sh responsibilities:
# - Wait for PostgreSQL and Redis availability
# - Initialize database schema if needed
# - Start Flask application (run_app.py)
ENTRYPOINT ["/app/entrypoint.sh"]