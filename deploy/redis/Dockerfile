# Redis 7 - Blacklist Intelligence Platform (cache-only, no persistence)
FROM redis:7-alpine

LABEL description="Redis 7 for Blacklist Intelligence Platform"

ARG APP_VERSION="0.0.0-dev"
ARG BUILD_DATE=""
ARG GIT_COMMIT="unknown"

LABEL org.opencontainers.image.version=${APP_VERSION}
LABEL org.opencontainers.image.revision=${GIT_COMMIT}
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.title="blacklist-redis"

RUN mkdir -p /usr/local/etc/redis && \
    printf '%s\n' \
        "bind 127.0.0.1" \
        "port 6379" \
        "protected-mode yes" \
        "maxmemory 256mb" \
        "maxmemory-policy allkeys-lru" \
        "appendonly no" \
        "save \"\"" \
        "tcp-keepalive 300" \
        "timeout 0" \
    > /usr/local/etc/redis/redis.conf

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD redis-cli ping | grep -q PONG || exit 1

EXPOSE 6379

CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
