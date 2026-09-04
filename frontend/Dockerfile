# ============================================================================
# Blacklist Next.js Frontend - Container Image
# ============================================================================
# Purpose: React-based modern frontend for IP blacklist/whitelist management
# Architecture: Multi-stage build for production optimization
# Framework: Next.js 15 (App Router), React 19, Tailwind CSS v4
# Dependencies: Flask API (blacklist-app:2542)
# Build context: project root (.) — NOT frontend/
# ============================================================================

# ============================================================================
# STAGE 1: Build Stage
# ============================================================================
FROM node:24-alpine AS builder
WORKDIR /app

COPY frontend/package*.json ./

RUN npm ci --legacy-peer-deps

COPY frontend/ .

ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ============================================================================
# STAGE 2: Production Runtime
# ============================================================================
FROM node:24-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Non-root runtime user; Compose maps host 443 to unprivileged container port 3000.
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy build artifacts
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder /app/server.js ./server.js
COPY --from=builder /app/server-routing.js ./server-routing.js
COPY frontend/entrypoint.sh ./entrypoint.sh

# Keep openssl for runtime SSL cert generation (entrypoint.sh)
# Remove system npm/npx/corepack — unused at runtime, carries known vulns
RUN apk upgrade --no-cache && apk add --no-cache openssl && \
    rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack && \
    rm -f /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack && \
    mkdir -p /app/ssl && \
    chown -R nextjs:nodejs /app/ssl

USER nextjs

EXPOSE 3000

ARG APP_VERSION="0.0.0-dev"
ARG GIT_COMMIT="unknown"
ARG BUILD_DATE=""

ENV APP_VERSION=${APP_VERSION}

LABEL org.opencontainers.image.version=${APP_VERSION}
LABEL org.opencontainers.image.revision=${GIT_COMMIT}
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.title="blacklist-frontend"
LABEL org.opencontainers.image.description="Blacklist Next.js Frontend"

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
# SSL file paths for self-signed cert generated in this image (not secrets)
ENV SSL_KEY_PATH=/app/ssl/server.key
ENV SSL_CERT_PATH=/app/ssl/server.crt

CMD ["sh", "entrypoint.sh"]
