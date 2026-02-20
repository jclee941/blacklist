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
# STAGE 1: Production Dependencies Only
# ============================================================================
FROM node:20-alpine AS deps
WORKDIR /app

COPY frontend/package*.json ./

RUN set -e && \
    for i in 1 2 3; do \
        if npm ci --only=production; then break; \
        else echo "Attempt $i failed, retrying..." && sleep 10; fi; \
        [ $i -eq 3 ] && exit 1; \
    done

# ============================================================================
# STAGE 2: Build Stage
# ============================================================================
FROM node:20-alpine AS builder
WORKDIR /app

COPY frontend/package*.json ./

RUN set -e && \
    for i in 1 2 3; do \
        if npm ci --legacy-peer-deps 2>/dev/null || npm install --legacy-peer-deps; then break; \
        else echo "Attempt $i failed, retrying..." && sleep 5; fi; \
        [ $i -eq 3 ] && exit 1; \
    done

COPY frontend/ .

ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ============================================================================
# STAGE 3: Production Runtime
# ============================================================================
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Non-root user with privileged port capability (443)
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs && \
    apk add --no-cache libcap && \
    setcap 'cap_net_bind_service=+ep' /usr/local/bin/node

# Copy build artifacts
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder /app/server.js ./server.js

RUN apk add --no-cache openssl && \
    mkdir -p /app/ssl && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout /app/ssl/server.key \
      -out /app/ssl/server.crt \
      -subj "/CN=blacklist/O=Blacklist/C=KR" >/dev/null 2>&1 && \
    chown -R nextjs:nodejs /app/ssl && \
    apk del openssl

USER nextjs

EXPOSE 443

ARG APP_VERSION="0.0.0-dev"
ARG GIT_COMMIT="unknown"
ARG BUILD_DATE=""

LABEL org.opencontainers.image.version=${APP_VERSION}
LABEL org.opencontainers.image.revision=${GIT_COMMIT}
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.title="blacklist-frontend"
LABEL org.opencontainers.image.description="Blacklist Next.js Frontend"

ENV PORT=443
ENV HOSTNAME="0.0.0.0"
ENV SSL_KEY_PATH=/app/ssl/server.key
ENV SSL_CERT_PATH=/app/ssl/server.crt

CMD ["node", "server.js"]
