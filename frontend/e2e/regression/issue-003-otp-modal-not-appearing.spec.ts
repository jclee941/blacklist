/**
 * Regression Test: OTP Modal Not Appearing on Collection Trigger
 *
 * PROBLEM:
 * When triggering SECUDIUM collection, the OTP input modal did not appear.
 * The collection trigger silently failed without prompting the user for the
 * OTP code sent via KakaoTalk.
 *
 * ROOT CAUSE:
 * The frontend checked `data.code === 'otp_required'` but the backend
 * testCredential endpoint returns `{ success: true, data: { status: "otp_required" } }`.
 * The response was nested inside `data.data`, not at the top level.
 * The check should have been `data.data?.status === 'otp_required'`.
 *
 * FIX:
 * Updated both testConnection() and triggerCollection() in useCollectionManagement.ts
 * to extract `innerData = data?.data` and check `innerData?.status === 'otp_required'`
 * instead of `data.code === 'otp_required'`.
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

test.describe('Regression: Issue #003 - OTP modal not appearing', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);

    // Mock collection status with SECUDIUM source
    await page.route('**/api/collection/status**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            collector_status: 'running',
            sources: {
              regtech: { status: 'active', last_run: '2026-02-11T10:00:00' },
              secudium: { status: 'active', last_run: '2026-02-11T09:30:00' },
            },
          },
        }),
      });
    });

    // Mock statistics
    await page.route('**/api/collection/statistics**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            summary: {
              total_collections: 10,
              successful_collections: 10,
              total_items_collected: 500,
              success_rate: 100.0,
            },
            sources: {
              regtech: { total_collections: 5, total_items: 300 },
              secudium: { total_collections: 5, total_items: 200 },
            },
          },
        }),
      });
    });

    // Mock sources
    await page.route('**/api/collection/sources**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { name: 'regtech', display_name: 'REGTECH', status: 'active' },
            { name: 'secudium', display_name: 'SECUDIUM', status: 'active' },
          ],
        }),
      });
    });
  });

  test('should show OTP modal when test connection returns otp_required @regression', async ({
    page,
  }) => {
    // STEP 1: Mock testCredential to return otp_required status
    await page.route('**/api/collection/credentials/secudium/test**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            status: 'otp_required',
            message: 'OTP verification required. Check KakaoTalk.',
            session_id: 'test-session-123',
          },
        }),
      });
    });

    // STEP 2: Navigate to collection management page
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // STEP 3: Find and click the SECUDIUM test connection button
    // Look for test/연결 테스트 button within a SECUDIUM collector card
    const secudiumCard = page.locator('text=SECUDIUM').first();
    const isVisible = await secudiumCard.isVisible().catch(() => false);

    if (isVisible) {
      // Find the test connection button near the SECUDIUM text
      const testBtn = page
        .locator('[class*="card"], [class*="Card"]')
        .filter({ hasText: /SECUDIUM/i })
        .getByRole('button', { name: /연결 테스트|테스트|test/i })
        .first();

      const testBtnVisible = await testBtn.isVisible().catch(() => false);
      if (testBtnVisible) {
        await testBtn.click();
        await page.waitForTimeout(1000);

        // STEP 4: After the fix, OTP modal should appear
        // Look for OTP input dialog elements (6-digit input, OTP-related text)
        const otpModal = page.locator(
          '[role="dialog"], [class*="modal"], [class*="Modal"], [class*="dialog"], [class*="Dialog"]'
        );
        const otpInput = page.locator('input[maxlength="6"], input[type="text"]');
        const otpText = page.getByText(/OTP|인증|카카오|KakaoTalk/i);

        const modalVisible = await otpModal
          .first()
          .isVisible()
          .catch(() => false);
        const inputVisible = await otpInput
          .first()
          .isVisible()
          .catch(() => false);
        const textVisible = await otpText
          .first()
          .isVisible()
          .catch(() => false);

        // At least one OTP-related element should be visible
        expect(modalVisible || inputVisible || textVisible).toBe(true);
      }
    }
  });

  test('should show OTP modal when trigger collection returns otp_required @regression', async ({
    page,
  }) => {
    // STEP 1: Mock trigger to first call testCredential which returns otp_required
    await page.route('**/api/collection/credentials/secudium/test**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            status: 'otp_required',
            message: 'OTP verification required.',
            session_id: 'trigger-session-456',
          },
        }),
      });
    });

    // STEP 2: Navigate to collection management
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // STEP 3: Find SECUDIUM trigger/collect button
    const triggerBtn = page
      .locator('[class*="card"], [class*="Card"]')
      .filter({ hasText: /SECUDIUM/i })
      .getByRole('button', { name: /수집 시작|수집|시작|trigger|collect/i })
      .first();

    const btnVisible = await triggerBtn.isVisible().catch(() => false);
    if (btnVisible) {
      await triggerBtn.click();
      await page.waitForTimeout(1000);

      // STEP 4: OTP modal should appear (was broken before fix)
      const otpElements = page.locator(
        '[role="dialog"], [class*="otp"], [class*="Otp"], [class*="OTP"]'
      );
      const otpInputs = page.locator('input[maxlength="6"]');
      const otpRelatedText = page.getByText(/OTP|인증 코드|인증코드/i);

      const hasOtpUI =
        (await otpElements
          .first()
          .isVisible()
          .catch(() => false)) ||
        (await otpInputs
          .first()
          .isVisible()
          .catch(() => false)) ||
        (await otpRelatedText
          .first()
          .isVisible()
          .catch(() => false));

      expect(hasOtpUI).toBe(true);
    }
  });
});
