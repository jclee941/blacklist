-- Migration: 010_tighten_ip_format_constraints.sql
-- Date: 2026-09-16
-- Description: Reject malformed IP literals at the database boundary.
--              The original blacklist_ips.valid_ip_format regex accepted any 1-3 digit
--              octet (999.999.999.999 passed) and whitelist_ips had no format check at
--              all. A single malformed entry fails an entire Cloudflare bulk PUT, which
--              stops the whole sync.
--              Additive per repository convention: the stricter constraint is added
--              alongside the existing one and declared NOT VALID so that pre-existing
--              rows do not block deployment. New and updated rows are checked.

DO $$
DECLARE
    invalid_rows BIGINT;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'blacklist_ips'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) LIKE '%25[0-5]%'
    ) THEN
        ALTER TABLE blacklist_ips
        ADD CONSTRAINT valid_ip_octet_range CHECK (
            ip_address ~ '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        ) NOT VALID;

        SELECT count(*) INTO invalid_rows
        FROM blacklist_ips
        WHERE ip_address !~ '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$';

        IF invalid_rows = 0 THEN
            ALTER TABLE blacklist_ips VALIDATE CONSTRAINT valid_ip_octet_range;
            RAISE NOTICE 'Added and validated: blacklist_ips.valid_ip_octet_range';
        ELSE
            RAISE WARNING 'blacklist_ips.valid_ip_octet_range left NOT VALID: % existing rows are malformed', invalid_rows;
        END IF;
    END IF;
END $$;

DO $$
DECLARE
    invalid_rows BIGINT;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'whitelist_ips'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) LIKE '%25[0-5]%'
    ) THEN
        -- IPv4 octet ranges, or a colon-form IPv6 literal, matching what the
        -- application's ipaddress-based validation accepts.
        ALTER TABLE whitelist_ips
        ADD CONSTRAINT whitelist_valid_ip_format CHECK (
            ip_address ~ '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            OR ip_address ~ '^[0-9A-Fa-f]{0,4}(:[0-9A-Fa-f]{0,4}){2,7}$'
        ) NOT VALID;

        SELECT count(*) INTO invalid_rows
        FROM whitelist_ips
        WHERE ip_address !~ '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
          AND ip_address !~ '^[0-9A-Fa-f]{0,4}(:[0-9A-Fa-f]{0,4}){2,7}$';

        IF invalid_rows = 0 THEN
            ALTER TABLE whitelist_ips VALIDATE CONSTRAINT whitelist_valid_ip_format;
            RAISE NOTICE 'Added and validated: whitelist_ips.whitelist_valid_ip_format';
        ELSE
            RAISE WARNING 'whitelist_ips.whitelist_valid_ip_format left NOT VALID: % existing rows are malformed', invalid_rows;
        END IF;
    END IF;
END $$;
