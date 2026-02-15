import { test, expect, type Page } from '@playwright/test';

/**
 * Live Secudium collection E2E test (no mocks).
 * Prerequisites: Collector with IMAP access for auto-OTP, valid Secudium credentials.
 */

const SECUDIUM_USERNAME = 'qws941_1';
const SECUDIUM_PASSWORD = 'bingogo1l7!';
const OTP_MODE = 'auto';
const COLLECTION_TIMEOUT = 180_000;

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

async function ensureSecudiumCredentials(page: Page) {
  const getRes = await page.request.get('/api/proxy/collection/credentials/secudium');
  const getCred = await getRes.json();

  const currentUsername = getCred?.data?.username;
  const currentOtpMode = getCred?.data?.otp_mode;
  const isEnabled = getCred?.data?.enabled;

  if (currentUsername === SECUDIUM_USERNAME && currentOtpMode === OTP_MODE && isEnabled === true) {
    return;
  }

  const putRes = await page.request.put('/api/proxy/collection/credentials/secudium', {
    data: {
      username: SECUDIUM_USERNAME,
      password: SECUDIUM_PASSWORD,
      enabled: true,
      collection_interval: 'daily',
      otp_mode: OTP_MODE,
    },
  });
  const putBody = await putRes.json();

  if (!putBody.success) {
    throw new Error(`Failed to save SECUDIUM credentials: ${JSON.stringify(putBody)}`);
  }
}

test.describe('Secudium 수집 실제 검증 (Live)', () => {
  test.setTimeout(COLLECTION_TIMEOUT);

  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await ensureSecudiumCredentials(page);
    await page.goto('/collection');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByText('수집 관리').first()).toBeVisible({ timeout: 15_000 });
  });

  test('SECUDIUM 수집 버튼으로 자동 OTP 수집이 완료된다', async ({ page }) => {
    // Given: SECUDIUM card with enabled 수집 button
    const secudiumCard = page
      .locator('div')
      .filter({ hasText: /^SECUDIUM/ })
      .filter({ has: page.getByRole('button', { name: '수집' }) })
      .first();
    await expect(secudiumCard).toBeVisible({ timeout: 15_000 });

    const collectBtn = secudiumCard.getByRole('button', { name: '수집' });
    await expect(collectBtn).toBeVisible({ timeout: 5_000 });
    await expect(collectBtn).toBeEnabled({ timeout: 10_000 });

    // When: Click 수집 and intercept trigger response
    const triggerResponsePromise = page.waitForResponse(
      (res) => res.url().includes('trigger/secudium') && res.request().method() === 'POST',
      { timeout: 30_000 }
    );
    await collectBtn.click();

    // Then: Trigger API returns success
    const triggerResponse = await triggerResponsePromise;
    const triggerBody = await triggerResponse.json();
    expect(triggerResponse.status()).toBe(200);
    expect(triggerBody.success).toBe(true);

    // Then: Success notification appears
    const successNotification = page.getByText(/SECUDIUM.*수집.*시작/);
    await expect(successNotification).toBeVisible({ timeout: 10_000 });

    await page.screenshot({
      path: 'test-results/secudium-collection-triggered.png',
      fullPage: false,
    });

    // Then: Collection completes (poll credential status)
    await expect(async () => {
      const statusRes = await page.request.get('/api/proxy/collection/credentials/secudium');
      const statusBody = await statusRes.json();
      expect(statusBody?.data?.connection_status).toBe('connected');
      expect(statusBody?.data?.last_collection).toBeTruthy();
    }).toPass({
      intervals: [5_000, 10_000, 10_000, 15_000, 15_000],
      timeout: COLLECTION_TIMEOUT - 30_000,
    });

    await page.screenshot({
      path: 'test-results/secudium-collection-complete.png',
      fullPage: false,
    });
  });

  test('SECUDIUM 수집 후 수집 이력이 갱신된다', async ({ page }) => {
    // Given: Current collection count
    const historyBefore = await page.request.get('/api/collection/statistics');
    const historyBeforeBody = await historyBefore.json();
    const secudiumCountBefore = historyBeforeBody?.data?.sources?.secudium?.total_collections ?? 0;

    // When: Trigger collection via 수집 button
    const secudiumCard = page
      .locator('div')
      .filter({ hasText: /^SECUDIUM/ })
      .filter({ has: page.getByRole('button', { name: '수집' }) })
      .first();
    const collectBtn = secudiumCard.getByRole('button', { name: '수집' });
    await expect(collectBtn).toBeEnabled({ timeout: 10_000 });

    const triggerResponsePromise = page.waitForResponse(
      (res) => res.url().includes('trigger/secudium') && res.request().method() === 'POST',
      { timeout: 30_000 }
    );
    await collectBtn.click();

    const triggerResponse = await triggerResponsePromise;
    expect(triggerResponse.status()).toBe(200);

    // Then: Collection count increments
    await expect(async () => {
      const historyAfter = await page.request.get('/api/collection/statistics');
      const historyAfterBody = await historyAfter.json();
      const secudiumCountAfter = historyAfterBody?.data?.sources?.secudium?.total_collections ?? 0;
      expect(secudiumCountAfter).toBeGreaterThan(secudiumCountBefore);
    }).toPass({
      intervals: [5_000, 10_000, 10_000, 15_000, 15_000],
      timeout: COLLECTION_TIMEOUT - 30_000,
    });
  });
});
