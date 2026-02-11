-- =============================================================================
-- Data Integrity Audit Queries
-- Blacklist Intelligence Platform
-- Created: 2026-02-11
-- Purpose: Verify detection_date, removal_date, detection_reason consistency
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. SECUDIUM IPs with NULL removal_date (should be detection_date + 3 months)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    ip_address,
    source,
    detection_date,
    removal_date,
    is_active,
    created_at
FROM blacklist_ips
WHERE source = 'SECUDIUM'
  AND removal_date IS NULL
ORDER BY created_at DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. SECUDIUM IPs where removal_date != detection_date + 3 months
--    (Finds entries that violate the +3 month rule)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    ip_address,
    source,
    detection_date,
    removal_date,
    detection_date + INTERVAL '3 months' AS expected_removal_date,
    removal_date - (detection_date + INTERVAL '3 months') AS date_diff,
    is_active,
    created_at
FROM blacklist_ips
WHERE source = 'SECUDIUM'
  AND detection_date IS NOT NULL
  AND removal_date IS NOT NULL
  AND removal_date != (detection_date + INTERVAL '3 months')::date
ORDER BY created_at DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. SECUDIUM IPs with NULL or empty detection_reason
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    ip_address,
    source,
    reason,
    detection_date,
    is_active,
    created_at
FROM blacklist_ips
WHERE source = 'SECUDIUM'
  AND (reason IS NULL OR TRIM(reason) = '')
ORDER BY created_at DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Any IP where removal_date < detection_date (constraint violation)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    ip_address,
    source,
    detection_date,
    removal_date,
    is_active,
    created_at
FROM blacklist_ips
WHERE removal_date IS NOT NULL
  AND detection_date IS NOT NULL
  AND removal_date < detection_date
ORDER BY source, created_at DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. Active IPs past their removal_date (should be deactivated)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    ip_address,
    source,
    detection_date,
    removal_date,
    is_active,
    updated_at
FROM blacklist_ips
WHERE is_active = true
  AND removal_date IS NOT NULL
  AND removal_date < CURRENT_DATE
ORDER BY removal_date ASC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. Active IPs older than 3 months with no removal_date
--    (Should have been deactivated by scheduler Rule 2)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    ip_address,
    source,
    detection_date,
    removal_date,
    is_active,
    created_at
FROM blacklist_ips
WHERE is_active = true
  AND removal_date IS NULL
  AND detection_date IS NOT NULL
  AND detection_date < CURRENT_DATE - INTERVAL '3 months'
ORDER BY detection_date ASC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. REGTECH IPs with NULL detection_date (should always have one)
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    ip_address,
    source,
    detection_date,
    removal_date,
    reason,
    is_active,
    created_at
FROM blacklist_ips
WHERE source = 'REGTECH'
  AND detection_date IS NULL
ORDER BY created_at DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. Summary statistics by source
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    source,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE is_active) AS active,
    COUNT(*) FILTER (WHERE NOT is_active) AS inactive,
    COUNT(*) FILTER (WHERE detection_date IS NULL) AS no_detection_date,
    COUNT(*) FILTER (WHERE removal_date IS NULL) AS no_removal_date,
    COUNT(*) FILTER (WHERE reason IS NULL OR TRIM(reason) = '') AS no_reason,
    COUNT(*) FILTER (WHERE is_active AND removal_date IS NOT NULL AND removal_date < CURRENT_DATE) AS expired_but_active,
    COUNT(*) FILTER (WHERE is_active AND detection_date IS NOT NULL AND detection_date < CURRENT_DATE - INTERVAL '3 months') AS older_than_3mo_active
FROM blacklist_ips
GROUP BY source
ORDER BY source;

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. FIX: Backfill SECUDIUM removal_date where missing
--    (Sets removal_date = detection_date + 3 months)
--    *** REVIEW BEFORE RUNNING ***
-- ─────────────────────────────────────────────────────────────────────────────
-- UPDATE blacklist_ips
-- SET removal_date = (detection_date + INTERVAL '3 months')::date,
--     updated_at = NOW()
-- WHERE source = 'SECUDIUM'
--   AND detection_date IS NOT NULL
--   AND removal_date IS NULL;

-- ─────────────────────────────────────────────────────────────────────────────
-- 10. FIX: Deactivate expired IPs that scheduler missed
--     *** REVIEW BEFORE RUNNING ***
-- ─────────────────────────────────────────────────────────────────────────────
-- UPDATE blacklist_ips
-- SET is_active = false,
--     updated_at = NOW()
-- WHERE is_active = true
--   AND (
--     (removal_date IS NOT NULL AND removal_date < CURRENT_DATE)
--     OR
--     (detection_date IS NOT NULL AND detection_date < CURRENT_DATE - INTERVAL '3 months')
--   );
