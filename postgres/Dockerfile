# PostgreSQL 15 - Blacklist Intelligence Platform
FROM postgres:15-alpine

LABEL description="PostgreSQL 15 for Blacklist Intelligence Platform"

ARG APP_VERSION="0.0.0-dev"
ARG BUILD_DATE=""
ARG GIT_COMMIT="unknown"

LABEL org.opencontainers.image.version=${APP_VERSION}
LABEL org.opencontainers.image.revision=${GIT_COMMIT}
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.title="blacklist-postgres"

ENV POSTGRES_DB=blacklist
ENV POSTGRES_USER=postgres
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

COPY initdb/ /docker-entrypoint-initdb.d/
COPY migrations/ /migrations/
COPY configure-tls.sh /usr/local/bin/configure-postgres-tls
COPY configure-tls.sh /docker-entrypoint-initdb.d/00-configure-tls.sh
COPY tls-entrypoint.sh /usr/local/bin/tls-entrypoint.sh
RUN chmod 755 \
    /usr/local/bin/configure-postgres-tls \
    /docker-entrypoint-initdb.d/00-configure-tls.sh \
    /usr/local/bin/tls-entrypoint.sh

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} || exit 1

EXPOSE 5432

ENTRYPOINT ["tls-entrypoint.sh"]
