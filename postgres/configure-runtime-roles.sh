#!/bin/sh
set -eu

: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${DB_OWNER_ROLE:?DB_OWNER_ROLE is required}"
: "${APP_DB_USER:?APP_DB_USER is required}"
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD is required}"
: "${COLLECTOR_DB_USER:?COLLECTOR_DB_USER is required}"
: "${COLLECTOR_DB_PASSWORD:?COLLECTOR_DB_PASSWORD is required}"

if [ "$POSTGRES_USER" = "$DB_OWNER_ROLE" ] ||
   [ "$POSTGRES_USER" = "$APP_DB_USER" ] ||
   [ "$POSTGRES_USER" = "$COLLECTOR_DB_USER" ] ||
   [ "$DB_OWNER_ROLE" = "$APP_DB_USER" ] ||
   [ "$DB_OWNER_ROLE" = "$COLLECTOR_DB_USER" ] ||
   [ "$APP_DB_USER" = "$COLLECTOR_DB_USER" ]; then
    printf 'database role names must be unique\n' >&2
    exit 2
fi

export PGPASSWORD="$POSTGRES_PASSWORD"
set -- --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"
if pg_isready --host=127.0.0.1 --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" >/dev/null 2>&1; then
    set -- --host=127.0.0.1 "$@"
fi
for migration in /migrations/007_align_ip_schema_contracts.sql /migrations/008_add_regtech_monitoring.sql; do
    if [ -f "$migration" ]; then
        psql "$@" --set=ON_ERROR_STOP=1 --file="$migration"
    fi
done
psql "$@" \
    --set=ON_ERROR_STOP=1 \
    --set=db_name="$POSTGRES_DB" \
    --set=db_owner="$DB_OWNER_ROLE" \
    --set=app_user="$APP_DB_USER" \
    --set=app_password="$APP_DB_PASSWORD" \
    --set=collector_user="$COLLECTOR_DB_USER" \
    --set=collector_password="$COLLECTOR_DB_PASSWORD" <<'SQL'
BEGIN;
SELECT format('CREATE ROLE %I NOLOGIN', :'db_owner')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'db_owner')
\gexec
SELECT format('ALTER ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS', :'db_owner')
\gexec
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
REVOKE CREATE ON SCHEMA public FROM :"app_user", :"collector_user";
GRANT CONNECT ON DATABASE :"db_name" TO :"app_user", :"collector_user";
GRANT USAGE, CREATE ON SCHEMA public TO :"db_owner";
GRANT USAGE ON SCHEMA public TO :"app_user";
GRANT USAGE ON SCHEMA public TO :"collector_user";
SELECT format('ALTER TABLE %I.%I OWNER TO %I', schemaname, tablename, :'db_owner')
FROM pg_tables WHERE schemaname = 'public'
\gexec
SELECT format('ALTER VIEW %I.%I OWNER TO %I', schemaname, viewname, :'db_owner')
FROM pg_views WHERE schemaname = 'public'
\gexec
SELECT format('ALTER SEQUENCE %I.%I OWNER TO %I', sequence_schema, sequence_name, :'db_owner')
FROM information_schema.sequences WHERE sequence_schema = 'public'
\gexec
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM :"app_user", :"collector_user";
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM :"app_user", :"collector_user";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"app_user";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO :"app_user";
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE blacklist_ips TO :"collector_user";
GRANT SELECT ON TABLE collection_credentials TO :"collector_user";
GRANT SELECT, INSERT, UPDATE ON TABLE collection_history, collection_stats, collection_status TO :"collector_user";
GRANT SELECT, INSERT ON TABLE regtech_monitoring, regtech_alerts TO :"collector_user";
GRANT USAGE, SELECT ON SEQUENCE blacklist_ips_id_seq, collection_history_id_seq, collection_stats_id_seq,
    collection_status_id_seq,
    regtech_monitoring_id_seq, regtech_alerts_id_seq TO :"collector_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"app_user" IN SCHEMA public REVOKE ALL ON TABLES FROM :"collector_user";
ALTER DEFAULT PRIVILEGES FOR ROLE :"app_user" IN SCHEMA public REVOKE ALL ON SEQUENCES FROM :"collector_user";
COMMIT;
SQL
