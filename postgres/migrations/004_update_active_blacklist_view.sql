-- Migration 004: Update active_blacklist view to include removal_date
-- Date: 2026-02-11
-- Description: Add removal_date column to the active_blacklist view

CREATE OR REPLACE VIEW active_blacklist AS
SELECT
    ip_address,
    reason,
    source,
    category,
    confidence_level,
    country,
    detection_date,
    removal_date,
    detection_count,
    last_seen,
    created_at
FROM blacklist_ips
WHERE is_active = TRUE
ORDER BY last_seen DESC, confidence_level DESC;
