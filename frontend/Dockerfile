# ============================================================================
# Blacklist Next.js Frontend - Container Image
# ============================================================================
# Purpose: React-based modern frontend for IP blacklist/whitelist management
# Version: 3.3.9
# Architecture: Multi-stage build for production optimization
# Framework: Next.js 14 (App Router), React 18, Tailwind CSS
# Dependencies: Flask API (blacklist-app:2542)
# ============================================================================

# ============================================================================
# STAGE 1: Production Dependencies Only
# ============================================================================
# Install only production dependencies (no devDependencies)
# Optimizes final image size by excluding build tools
# ============================================================================
FROM node:20-alpine AS deps
WORKDIR /app

COPY package*.json ./

# Install production dependencies with retry mechanism
RUN set -e && \
    echo "🔍 Installing production dependencies..." && \
    for i in 1 2 3; do \
        if npm ci --only=production; then \
            echo "✅ Production dependencies installed" && \
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
# STAGE 2: Build Stage
# ============================================================================
# Install all dependencies (including devDependencies for building)
# Build Next.js application with optimizations
# ============================================================================
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./

# Install all dependencies with retry mechanism
RUN set -e && \
    echo "🔍 Installing build dependencies..." && \
    for i in 1 2 3; do \
        if npm ci --legacy-peer-deps 2>/dev/null || npm install --legacy-peer-deps; then \
            echo "✅ Build dependencies installed" && \
            break; \
        else \
            echo "⚠️ Installation attempt $i failed, retrying in 5s..." && \
            sleep 5; \
        fi; \
        if [ $i -eq 3 ]; then \
            echo "❌ Failed to install dependencies after 3 attempts" && \
            exit 1; \
        fi; \
    done

# Copy source code
COPY . .

# Disable Next.js telemetry (privacy)
ENV NEXT_TELEMETRY_DISABLED=1

# Build Next.js application
RUN set -e && \
    echo "🔍 Building Next.js application..." && \
    npm run build && \
    echo "✅ Next.js build completed"

# ============================================================================
# STAGE 3: Production Runtime
# ============================================================================
# Minimal production image with only runtime artifacts
# Security: Non-root user (nextjs:nodejs)
# ============================================================================
FROM node:20-alpine AS runner
WORKDIR /app

# Production environment settings
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# ============================================================================
# Security: Non-Root User Creation with privileged port capability
# ============================================================================
# Create nodejs group (GID 1001) and nextjs user (UID 1001)
# Add capability to bind to privileged ports (443)
# ============================================================================
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs && \
    apk add --no-cache libcap && \
    setcap 'cap_net_bind_service=+ep' /usr/local/bin/node

# ============================================================================
# Copy Build Artifacts from Builder Stage
# ============================================================================
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder /app/server.js ./server.js

RUN mkdir -p /app/ssl

# Switch to non-root user
USER nextjs

# ============================================================================
# Network Port Configuration
# ============================================================================
# Port 443: Next.js application server (privileged port for airgap)
# ============================================================================
EXPOSE 443

ARG APP_VERSION="0.0.0-dev"
ARG GIT_COMMIT="unknown"
ARG BUILD_DATE=""

LABEL org.opencontainers.image.version=${APP_VERSION}
LABEL org.opencontainers.image.revision=${GIT_COMMIT}
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.title="blacklist-frontend"
LABEL org.opencontainers.image.description="Blacklist Next.js Frontend"

# ============================================================================
# Environment Variables Configuration
# ============================================================================
# Port: 443 (frontend service - airgap)
# Hostname: 0.0.0.0 (listen on all network interfaces)
# Backend API: http://blacklist-app:2542 (Flask API, via Docker network)
# ============================================================================
ENV PORT=443
ENV HOSTNAME="0.0.0.0"

# ============================================================================
# Default Command: Start Next.js Server
# ============================================================================
# server.js: Next.js standalone server (generated by build)
# Handles SSR (Server-Side Rendering) and API routes
# ============================================================================
CMD ["node", "server.js"]
