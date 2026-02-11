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

test.describe('Collection Page - Basic Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');
  });

  test('should display collection page with header', async ({ page }) => {
    await expect(page.locator('h1').filter({ hasText: '데이터 수집' })).toBeVisible();
    await expect(page.getByText('블랙리스트 데이터 수집 관리 및 이력')).toBeVisible();
  });

  test('should display all 2 tabs', async ({ page }) => {
    await expect(page.getByRole('tab', { name: '수집 관리' })).toBeVisible();
    await expect(page.getByRole('tab', { name: '수집 이력' })).toBeVisible();
  });

  test('should default to management tab selected', async ({ page }) => {
    const managementTab = page.getByRole('tab', { name: '수집 관리' });
    await expect(managementTab).toHaveAttribute('aria-selected', 'true');
  });
});

test.describe('Collection Page - Tab Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');
  });

  test('should switch to history tab when clicked', async ({ page }) => {
    const historyTab = page.getByRole('tab', { name: '수집 이력' });
    await historyTab.click();
    await page.waitForTimeout(500);
    await expect(historyTab).toHaveAttribute('aria-selected', 'true');
  });
});

test.describe('Collection Management Tab', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');
  });

  test('should display collection status', async ({ page }) => {
    await expect(page.getByText('수집 상태')).toBeVisible();
  });

  test('should display collection stats cards', async ({ page }) => {
    await page.waitForTimeout(1000);
    const hasCard = await page
      .getByText('수집 상태')
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasCard).toBe(true);
  });

  test('should display active collector count', async ({ page }) => {
    await expect(page.getByText('활성 수집기')).toBeVisible();
  });
});

test.describe('Collection History Tab', () => {
  test('should display history tab content', async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');

    await page.getByRole('tab', { name: '수집 이력' }).click();
    await page.waitForTimeout(500);
    await expect(page.getByRole('tab', { name: '수집 이력' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
  });
});

test.describe('Collection Page - Responsive', () => {
  test('should be accessible on mobile', async ({ page, isMobile }) => {
    test.skip(!isMobile, 'Mobile only test');

    await loginViaApi(page);
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('h1').filter({ hasText: '데이터 수집' })).toBeVisible();
  });
});
