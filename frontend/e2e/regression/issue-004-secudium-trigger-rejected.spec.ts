/**
 * Regression Test: SECUDIUM Trigger Rejected by Backend
 *
 * PROBLEM:
 * When triggering a SECUDIUM collection from the frontend, the backend
 * returned a ValidationError because "secudium" was not in the allowed
 * source values.
 *
 * ROOT CAUSE:
 * `trigger.py:25` only allowed `["REGTECH", "ALL"]` as valid source values.
 * SECUDIUM was missing from the allowed list, causing the backend to reject
 * any SECUDIUM trigger request with a validation error.
 *
 * FIX:
 * Added "SECUDIUM" to the allowed values in trigger.py:
 * `["REGTECH", "SECUDIUM", "ALL"]`
 */

import { test, expect, type Page } from '@playwright/test';

async function loginViaApi(page: Page) {
  const res = await page.request.post('/api/auth/login', {
    data: { username: 'admin', password: 'admin' },
  });
  const body = await res.json();
  const token = body.data?.token || body.token;
  if (token) {
    await page.goto('/');
    await page.evaluate((t) => localStorage.setItem('blacklist_auth_token', t), token);
    await page.reload();
    await page.waitForLoadState('networkidle');
  }
}

test.describe('Regression: Issue #004 - SECUDIUM trigger rejected by backend', () => {
  test('should accept SECUDIUM as a valid trigger source via API @regression', async ({ page }) => {
    await loginViaApi(page);

    // STEP 1: Directly call the trigger API with SECUDIUM source
    // Before the fix, this returned a validation error
    const res = await page.request.post('/api/collection/trigger/secudium', {
      data: { force: true },
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const status = res.status();
    const body = await res.json().catch(() => ({}));

    // STEP 2: The response should NOT be a 400 validation error about invalid source
    // Before fix: { error: "Invalid source. Allowed values: REGTECH, ALL" }
    // After fix: Should accept the request (may still fail for other reasons like
    // credentials, but should NOT fail with "invalid source" validation error)
    if (status === 400) {
      const errorMsg = body.message || body.error || JSON.stringify(body);
      // Should NOT contain "invalid source" or "allowed values: REGTECH, ALL"
      expect(errorMsg.toLowerCase()).not.toContain('invalid source');
      expect(errorMsg.toLowerCase()).not.toContain('allowed values: regtech, all');
    }

    // Valid responses: 200 (success), 202 (accepted), 401 (auth needed),
    // 400 (other validation like missing credentials), 500 (collector error)
    // But NOT 400 specifically about invalid source
    expect([200, 202, 400, 401, 403, 500, 502, 503]).toContain(status);
  });

  test('should still accept REGTECH as a valid trigger source @regression', async ({ page }) => {
    await loginViaApi(page);

    // Verify REGTECH still works (no regression from adding SECUDIUM)
    const res = await page.request.post('/api/collection/trigger/regtech', {
      data: { force: true },
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const status = res.status();
    const body = await res.json().catch(() => ({}));

    if (status === 400) {
      const errorMsg = body.message || body.error || JSON.stringify(body);
      expect(errorMsg.toLowerCase()).not.toContain('invalid source');
    }
  });

  test('should still reject unknown source names @regression', async ({ page }) => {
    await loginViaApi(page);

    // Unknown sources should still be rejected
    const res = await page.request.post('/api/collection/trigger/unknown_source', {
      data: { force: true },
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const status = res.status();
    // Unknown source should get a 400 validation error
    expect(status).toBe(400);
  });
});
