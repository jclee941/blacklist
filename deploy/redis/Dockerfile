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
        "port 0" \
        "tls-port 6379" \
        "tls-cert-file /run/blacklist/tls/tls.crt" \
        "tls-key-file /run/blacklist/tls/tls.key" \
        "tls-ca-cert-file /run/blacklist/ca.crt" \
        "tls-auth-clients no" \
        "protected-mode yes" \
        "maxmemory 256mb" \
        "maxmemory-policy noeviction" \
        "appendonly yes" \
        "appendfsync everysec" \
        "save 900 1" \
        "tcp-keepalive 300" \
        "timeout 0" \
    > /usr/local/etc/redis/redis.conf

EXPOSE 6379

CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
