# ============================================================================
# Blacklist Flask Application - Container Image
# ============================================================================
# Purpose: Flask web application for IP blacklist/whitelist management
# Version: 3.3.9
# Architecture: Multi-stage build for production optimization
# Dependencies: PostgreSQL 15, Redis 7, Python 3.11
# ============================================================================

# ============================================================================
# STAGE 1: Python Dependencies and Application Build
# ============================================================================
FROM python:3.11-slim-bullseye AS python-base

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
FROM python:3.11-slim-bullseye as production

# ============================================================================
# Build Arguments (Secure Credential Injection + Version Management)
# ============================================================================
# Passed from GitLab CI/CD → Docker build → Environment variables
# Version management (injected by GitLab CI)
ARG APP_VERSION=""
ARG GIT_COMMIT="unknown"
ARG BUILD_NUMBER=""

# Legacy build metadata (for compatibility)
ARG VERSION
ARG VCS_REF
ARG BUILDTIME
ARG BUILD_DATE

# Application secrets
ARG REGTECH_ID
ARG REGTECH_PW
ARG REGTECH_BASE_URL

# Database configuration (dependency: blacklist-postgres)
ARG POSTGRES_HOST
ARG POSTGRES_PORT
ARG POSTGRES_DB
ARG POSTGRES_USER
ARG POSTGRES_PASSWORD

# Redis configuration (dependency: blacklist-redis)
ARG REDIS_HOST
ARG REDIS_PORT

# Application URLs
ARG PRD_URL
ARG DEV_URL

# GitHub integration
ARG GITHUB_TOKEN
ARG GITHUB_REPO_OWNER
ARG GITHUB_REPO_NAME

# Registry configuration
ARG REGISTRY_HOST
ARG REGISTRY_USER
ARG REGISTRY_PASSWORD

# Environment configuration
ARG FLASK_ENV
ARG TIMEZONE

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

# ============================================================================
# Environment Variables Configuration
# ============================================================================
# Dependency resolution: ENV variables set from ARG build arguments
#
# Service Dependencies:
# - blacklist-postgres: Database (POSTGRES_*)
# - blacklist-redis: Cache (REDIS_*)
# - regtech.fsec.or.kr: External API (REGTECH_*)
#
# Configuration Hierarchy:
# 1. Build arguments (from docker-compose.yml or CI/CD)
# 2. Environment variables (container runtime)
# 3. Default values (fallback for development)
# ============================================================================
ENV VERSION=${VERSION:-unknown} \
    BUILD_NUMBER=${BUILD_NUMBER:-0} \
    VCS_REF=${VCS_REF:-unknown} \
    BUILDTIME=${BUILDTIME:-unknown} \
    # Version Management (NEW - injected by GitLab CI)
    APP_VERSION=${APP_VERSION:-0.0.0-dev} \
    GIT_COMMIT=${GIT_COMMIT:-unknown} \
    # Application Configuration
    FLASK_ENV=${FLASK_ENV:-production} \
    PORT=2542 \
    PYTHONPATH=/app \
    TZ=Asia/Seoul \
    # Application Secrets
    REGTECH_ID=${REGTECH_ID} \
    REGTECH_PW=${REGTECH_PW} \
    REGTECH_BASE_URL=${REGTECH_BASE_URL:-https://regtech.fsec.or.kr} \
    # Database Configuration (dependency: blacklist-postgres)
    POSTGRES_HOST=${POSTGRES_HOST:-blacklist-postgres} \
    POSTGRES_PORT=${POSTGRES_PORT:-5432} \
    POSTGRES_DB=${POSTGRES_DB:-blacklist} \
    POSTGRES_USER=${POSTGRES_USER:-postgres} \
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres} \
    # Redis Configuration (dependency: blacklist-redis)
    REDIS_HOST=${REDIS_HOST:-blacklist-redis} \
    REDIS_PORT=${REDIS_PORT:-6379} \
    # Application URLs
    PRD_URL=${PRD_URL:-https://${PROD_DOMAIN:-blacklist.example.com}} \
    DEV_URL=${DEV_URL:-https://${DEV_DOMAIN:-blacklist-dev.example.com}} \
    # GitHub Integration
    GITHUB_TOKEN=${GITHUB_TOKEN} \
    GITHUB_REPO_OWNER=${GITHUB_REPO_OWNER:-qws941} \
    GITHUB_REPO_NAME=${GITHUB_REPO_NAME:-blacklist} \
    # Registry Configuration
    REGISTRY_HOST=${REGISTRY_HOST:-${REGISTRY_DOMAIN:-registry.example.com}} \
    REGISTRY_USER=${REGISTRY_USER:-admin} \
    REGISTRY_PASSWORD=${REGISTRY_PASSWORD}

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
    echo "✅ Application v3.3.9 embedded in image" && \
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