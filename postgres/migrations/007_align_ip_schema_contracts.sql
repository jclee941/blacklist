ALTER TABLE whitelist_ips
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

UPDATE whitelist_ips
SET is_active = TRUE
WHERE is_active IS NULL;

ALTER TABLE whitelist_ips
ALTER COLUMN is_active SET DEFAULT TRUE;

ALTER TABLE whitelist_ips
ALTER COLUMN is_active SET NOT NULL;

ALTER TABLE blacklist_ips
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

UPDATE blacklist_ips
SET is_active = TRUE
WHERE is_active IS NULL;

ALTER TABLE blacklist_ips
ALTER COLUMN is_active SET DEFAULT TRUE;

ALTER TABLE blacklist_ips
ALTER COLUMN is_active SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_whitelist_ips_ip_unique
ON whitelist_ips(ip_address);

CREATE UNIQUE INDEX IF NOT EXISTS idx_blacklist_ips_ip_source_unique
ON blacklist_ips(ip_address, source);
