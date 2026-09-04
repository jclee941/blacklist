#!/bin/sh
set -eu

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${APP_DB_USER:?APP_DB_USER is required}"
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD is required}"
: "${COLLECTOR_DB_USER:?COLLECTOR_DB_USER is required}"
: "${COLLECTOR_DB_PASSWORD:?COLLECTOR_DB_PASSWORD is required}"

export PGPASSWORD="$POSTGRES_PASSWORD"
set -- --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"
if pg_isready --host=127.0.0.1 --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" >/dev/null 2>&1; then
    set -- --host=127.0.0.1 "$@"
fi
psql "$@" \
    --set=ON_ERROR_STOP=1 \
    --set=db_name="$POSTGRES_DB" \
    --set=app_user="$APP_DB_USER" \
    --set=app_password="$APP_DB_PASSWORD" \
    --set=collector_user="$COLLECTOR_DB_USER" \
    --set=collector_password="$COLLECTOR_DB_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user')
\gexec
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'collector_user', :'collector_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'collector_user')
\gexec
SELECT format('ALTER ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS', :'app_user', :'app_password')
\gexec
SELECT format('ALTER ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS', :'collector_user', :'collector_password')
\gexec
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db_name" TO :"app_user", :"collector_user";
GRANT USAGE, CREATE ON SCHEMA public TO :"app_user";
GRANT USAGE ON SCHEMA public TO :"collector_user";
SELECT format('ALTER TABLE %I.%I OWNER TO %I', schemaname, tablename, :'app_user')
FROM pg_tables WHERE schemaname = 'public'
\gexec
SELECT format('ALTER SEQUENCE %I.%I OWNER TO %I', sequence_schema, sequence_name, :'app_user')
FROM information_schema.sequences WHERE sequence_schema = 'public'
\gexec
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"app_user";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO :"app_user";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"collector_user";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO :"collector_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"app_user" IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"collector_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"app_user" IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"collector_user";
SQL
