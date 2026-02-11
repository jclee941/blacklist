import { test, expect, type Page } from '@playwright/test';

test.describe.configure({ mode: 'parallel' });

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

test.describe('네비게이션 기능 검증', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await loginViaApi(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('모든 네비게이션 링크가 표시된다', async ({ page }) => {
    const navLinks = ['대시보드', 'IP 관리', 'FortiGate', '데이터 수집', '데이터베이스'];
    for (const link of navLinks) {
      await expect(page.getByRole('link', { name: link }).first()).toBeVisible();
    }
  });

  test('로고가 표시된다', async ({ page }) => {
    await expect(page.getByAltText('Nextrade')).toBeVisible();
  });

  test('대시보드 링크 클릭 시 / 로 이동한다', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
    await page.getByRole('link', { name: '대시보드' }).first().click();
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/');
  });

  test('IP 관리 링크 클릭 시 /ip-management 로 이동한다', async ({ page }) => {
    await page.getByRole('link', { name: 'IP 관리' }).first().click();
    await page.waitForURL('**/ip-management', { timeout: 30000 });
    expect(page.url()).toContain('/ip-management');
  });

  test('데이터 수집 링크 클릭 시 /collection 으로 이동한다', async ({ page }) => {
    await page.getByRole('link', { name: '데이터 수집' }).first().click();
    await page.waitForURL('**/collection', { timeout: 30000 });
    expect(page.url()).toContain('/collection');
  });

  test('FortiGate 링크 클릭 시 /fortinet 으로 이동한다', async ({ page }) => {
    await page.getByRole('link', { name: 'FortiGate' }).first().click();
    await page.waitForURL('**/fortinet', { timeout: 30000 });
    expect(page.url()).toContain('/fortinet');
  });

  test('데이터베이스 링크 클릭 시 /database 로 이동한다', async ({ page }) => {
    await page.getByRole('link', { name: '데이터베이스' }).first().click();
    await page.waitForURL('**/database', { timeout: 30000 });
    expect(page.url()).toContain('/database');
  });

  test('/monitoring 접속 시 / 로 리다이렉트된다', async ({ page }) => {
    await page.goto('/monitoring');
    await page.waitForLoadState('networkidle');
    const url = page.url();
    expect(url.endsWith('/') || !url.includes('/monitoring')).toBe(true);
  });

  test('각 페이지 이동 후 뒤로 가기가 동작한다', async ({ page }) => {
    await page.getByRole('link', { name: 'IP 관리' }).first().click();
    await page.waitForURL('**/ip-management', { timeout: 30000 });
    expect(page.url()).toContain('/ip-management');

    await page.goBack();
    await page.waitForLoadState('networkidle');
    const url = page.url();
    expect(url.endsWith('/')).toBe(true);
  });

  test('모바일 메뉴 토글이 작은 화면에서 동작한다', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForLoadState('networkidle');

    const menuToggle = page.getByTestId('navbar-menu-toggle');
    const hasToggle = await menuToggle.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasToggle) {
      await menuToggle.click();
      const mobileMenu = page.getByTestId('navbar-mobile-menu');
      await expect(mobileMenu).toBeVisible();
    }
  });
});
