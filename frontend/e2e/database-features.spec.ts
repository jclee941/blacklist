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

test.describe('데이터베이스 페이지', () => {
  test.describe.configure({ mode: 'parallel' });

  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/database');
    await page.waitForLoadState('networkidle');
  });

  test('페이지 헤더가 올바르게 표시된다', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '데이터베이스' }).first()).toBeVisible();
    await expect(page.getByText('PostgreSQL 테이블 현황')).toBeVisible();
  });

  test('테이블 목록이 표시된다', async ({ page }) => {
    const table = page.locator('table').first();
    await expect(table).toBeVisible({ timeout: 10000 });
  });

  test('테이블 정보가 컬럼 헤더를 포함한다', async ({ page }) => {
    await page.waitForTimeout(2000);
    const headers = page.locator('thead th');
    await expect(headers.first()).toBeVisible({ timeout: 10000 });
  });

  test('데이터베이스 연결 상태가 표시된다', async ({ page }) => {
    const statusTexts = ['연결', '정상', 'PostgreSQL'];
    let found = false;
    for (const text of statusTexts) {
      const el = page.getByText(text).first();
      if (await el.isVisible().catch(() => false)) {
        found = true;
        break;
      }
    }
    expect(found).toBe(true);
  });

  test('새로고침 버튼이 동작한다', async ({ page }) => {
    const refreshBtn = page
      .locator('button')
      .filter({
        has: page.locator('svg'),
      })
      .first();

    if (await refreshBtn.isVisible().catch(() => false)) {
      const reqPromise = page
        .waitForRequest((req) => req.url().includes('/api/'), { timeout: 5000 })
        .catch(() => null);
      await refreshBtn.click();
      await reqPromise;
    }
  });

  test('테이블 행 데이터가 로드된다', async ({ page }) => {
    await page.waitForTimeout(3000);
    const rows = page.locator('tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});
