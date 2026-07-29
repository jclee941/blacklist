#!/bin/sh
set -eu

if [ -s "${PGDATA}/PG_VERSION" ]; then
    configure-postgres-tls
fi

exec docker-entrypoint.sh "$@"
