-- Migration: 009_add_blacklist_change_notify.sql
-- Date: 2026-09-16
-- Description: Publish blacklist_changes notifications for the Cloudflare push service.
--              CloudflarePushService issues LISTEN blacklist_changes; without these
--              triggers no notification is ever emitted and the list never syncs.
--              Statement-level triggers keep a bulk upsert to a single notification.

CREATE OR REPLACE FUNCTION notify_blacklist_changes() RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM pg_notify('blacklist_changes', TG_TABLE_NAME || ':' || TG_OP);
    RETURN NULL;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'blacklist_ips'::regclass
          AND tgname = 'blacklist_ips_notify_changes'
    ) THEN
        CREATE TRIGGER blacklist_ips_notify_changes
        AFTER INSERT OR UPDATE OR DELETE ON blacklist_ips
        FOR EACH STATEMENT EXECUTE FUNCTION notify_blacklist_changes();
        RAISE NOTICE 'Added: blacklist_ips_notify_changes trigger';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'whitelist_ips'::regclass
          AND tgname = 'whitelist_ips_notify_changes'
    ) THEN
        CREATE TRIGGER whitelist_ips_notify_changes
        AFTER INSERT OR UPDATE OR DELETE ON whitelist_ips
        FOR EACH STATEMENT EXECUTE FUNCTION notify_blacklist_changes();
        RAISE NOTICE 'Added: whitelist_ips_notify_changes trigger';
    END IF;
END $$;
