-- Migration 006: Fix is_active inconsistency for IPs with future removal_date
-- Date: 2026-02-18
-- Issue: IPs have removal_date >= CURRENT_DATE but is_active = false

UPDATE blacklist_ips
SET is_active = true, updated_at = NOW()
WHERE removal_date >= CURRENT_DATE
  AND is_active = false;
