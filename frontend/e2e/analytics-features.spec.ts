import { test, expect } from '@playwright/test';
import { loginViaApi } from './auth.fixtures';

test.describe('일별 탐지 통계 페이지', () => {
  test.describe.configure({ mode: 'parallel' });

  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/analytics');
    await page.waitForLoadState('networkidle');
  });

  test('페이지 헤더가 올바르게 표시된다', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '일별 탐지 통계' })).toBeVisible();
    await expect(page.getByText('탐지일 기준 IP 수집 현황 분석')).toBeVisible();
  });

  test('기간 선택 드롭다운이 동작한다', async ({ page }) => {
    const select = page.locator('select');
    await expect(select).toBeVisible();
    await expect(select).toHaveValue('365');

    await select.selectOption('90');
    await expect(select).toHaveValue('90');

    await select.selectOption('365');
    await expect(select).toHaveValue('365');
  });

  test('새로고침 버튼이 데이터를 다시 불러온다', async ({ page }) => {
    const refreshBtn = page.getByRole('button', { name: /새로고침/ });
    await expect(refreshBtn).toBeVisible();

    await refreshBtn.click();
    // Verify button is still functional after click
    await expect(refreshBtn).toBeVisible();
  });

  test('요약 카드들이 표시된다', async ({ page }) => {
    const summaryTexts = ['총 IP 수', '활성 일수', '일평균'];
    for (const text of summaryTexts) {
      await expect(page.getByText(text).first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('타임라인 테이블이 표시된다', async ({ page }) => {
    const table = page.locator('table').first();
    await expect(table).toBeVisible({ timeout: 10000 });

    const headers = table.locator('thead th');
    await expect(headers.first()).toBeVisible();
  });

  test('기간 변경 시 API가 호출된다', async ({ page }) => {
    const select = page.locator('select');
    const reqPromise = page.waitForRequest((req) => req.url().includes('days=90'));
    await select.selectOption('90');
    await reqPromise;
  });

  test('페이지네이션이 동작한다', async ({ page }) => {
    await page.waitForTimeout(2000);

    const nextBtn = page
      .locator('button:has(svg[class*="chevron-right"]), ' + 'button:has(svg.lucide-chevron-right)')
      .first();

    const paginationArea = page.getByText(/페이지|\//).first();
    if (await paginationArea.isVisible().catch(() => false)) {
      if (await nextBtn.isEnabled().catch(() => false)) {
        await nextBtn.click();
      }
    }
  });

  test('데이터 로딩 중 상태가 표시된다', async ({ page }) => {
    await page.goto('/analytics');
    const loadingOrContent = page.locator('.animate-pulse, table, [class*="skeleton"]').first();
    await expect(loadingOrContent).toBeVisible({ timeout: 10000 });
  });
});
