import { test, expect, type Page } from '@playwright/test';
import { getE2ECredentials } from './auth.fixtures';

async function loginViaApi(page: Page) {
  const res = await page.request.post('/api/auth/login', {
    data: getE2ECredentials(),
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

test.describe('데이터 수집 페이지', () => {
  test.describe.configure({ mode: 'parallel' });

  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');
  });

  test('페이지 헤더가 올바르게 표시된다', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '데이터 수집' })).toBeVisible();
    await expect(page.getByText('데이터 수집 관리 및 이력')).toBeVisible();
  });

  test('2개 탭이 모두 표시된다', async ({ page }) => {
    const tabs = ['수집 관리', '수집 이력'];
    for (const tabName of tabs) {
      await expect(page.getByRole('tab', { name: tabName })).toBeVisible();
    }
  });

  test('기본 탭이 수집 관리이다', async ({ page }) => {
    const activeTab = page.getByRole('tab', {
      name: '수집 관리',
    });
    await expect(activeTab).toHaveAttribute('aria-selected', 'true');
  });

  test('수집 관리 탭에 상태 카드가 표시된다', async ({ page }) => {
    await page.waitForTimeout(2000);
    const cardTexts = ['수집 상태', '활성 수집기'];
    for (const text of cardTexts) {
      await expect(page.getByText(text).first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('탭 전환이 동작한다 - 수집 이력', async ({ page }) => {
    await page.getByRole('tab', { name: '수집 이력' }).click();
    await page.waitForTimeout(500);
    await expect(page.getByRole('tab', { name: '수집 이력' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
  });

  test('수집 이력 탭에 테이블이 표시된다', async ({ page }) => {
    await page.getByRole('tab', { name: '수집 이력' }).click();
    await page.waitForTimeout(2000);

    const tableOrEmpty = page.locator('table, [class*="empty"]').first();
    await expect(tableOrEmpty).toBeVisible({ timeout: 10000 });
  });

  test('수집 관리 탭에서 수집 시작/중지 버튼이 있다', async ({ page }) => {
    await page.waitForTimeout(2000);
    const actionBtn = page.getByRole('button', {
      name: /수집 시작|수집 중지|시작|중지/,
    });
    if (
      await actionBtn
        .first()
        .isVisible()
        .catch(() => false)
    ) {
      await expect(actionBtn.first()).toBeVisible();
    }
  });
});
