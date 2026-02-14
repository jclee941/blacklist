import { test, expect, Page } from '@playwright/test';

/**
 * Live OTP modal test against real 220d sandbox API (no mocks).
 * SECUDIUM testCredential returns otp_required → OTP modal must appear.
 */

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
    await page.waitForLoadState('domcontentloaded');
  }
}

test.describe('OTP 모달 실제 검증 (220d Live)', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/collection');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText('수집 관리').first()).toBeVisible({ timeout: 15000 });
  });

  test('SECUDIUM 연결 테스트 시 OTP 모달이 나타난다', async ({ page }) => {
    // Find card containing both "SECUDIUM" text and "테스트" button
    const secudiumCard = page
      .locator('div')
      .filter({ hasText: /^SECUDIUM/ })
      .filter({ has: page.getByRole('button', { name: '테스트' }) })
      .first();
    await expect(secudiumCard).toBeVisible({ timeout: 10000 });

    const testButton = secudiumCard.getByRole('button', { name: '테스트' });
    await expect(testButton).toBeVisible({ timeout: 5000 });

    // Intercept API response to confirm otp_required
    const responsePromise = page.waitForResponse(
      (res) => res.url().includes('credential') || res.url().includes('test-auth'),
      { timeout: 15000 }
    );

    await testButton.click();

    const response = await responsePromise.catch(() => null);
    if (response) {
      const body = await response.json().catch(() => null);
      console.log('API response:', JSON.stringify(body));
    }

    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'test-results/otp-modal-after-click.png', fullPage: false });

    const otpVisible =
      (await page
        .getByText(/OTP/)
        .isVisible()
        .catch(() => false)) ||
      (await page
        .locator('input[maxlength="6"]')
        .isVisible()
        .catch(() => false)) ||
      (await page
        .locator('[role="dialog"]')
        .isVisible()
        .catch(() => false)) ||
      (await page
        .getByText('인증 코드')
        .isVisible()
        .catch(() => false)) ||
      (await page
        .getByText('인증코드')
        .isVisible()
        .catch(() => false));

    await page.screenshot({ path: 'test-results/otp-modal-live.png', fullPage: false });

    expect(otpVisible).toBe(true);
  });
});
