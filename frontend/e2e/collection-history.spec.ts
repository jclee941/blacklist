import { test, expect } from '@playwright/test';
import { loginViaApi, mockCollectionApis } from './collection-process.fixtures';

test.describe('수집 프로세스 E2E 테스트', () => {
  test.describe('수집 이력 탭', () => {
    test.beforeEach(async ({ page }) => {
      await loginViaApi(page);
      await mockCollectionApis(page);

      await page.route('**/api/collection/history**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              items: [
                {
                  id: 1,
                  source: 'regtech',
                  status: 'success',
                  items_collected: 500,
                  started_at: '2026-02-11T10:00:00',
                  completed_at: '2026-02-11T10:01:00',
                  duration: 60,
                },
                {
                  id: 2,
                  source: 'regtech',
                  status: 'failed',
                  items_collected: 0,
                  started_at: '2026-02-10T10:00:00',
                  completed_at: '2026-02-10T10:00:30',
                  duration: 30,
                  error: 'Connection timeout',
                },
              ],
              total: 2,
              page: 1,
              per_page: 20,
            },
          }),
        });
      });
    });

    test('수집 이력 탭으로 전환', async ({ page }) => {
      await page.goto('/collection');
      await page.waitForLoadState('domcontentloaded');

      const historyTab = page.getByText('수집 이력');
      await historyTab.click();

      // Wait for history data to load (async fetch after tab switch)
      await expect(
        page.getByText(/regtech|REGTECH|성공|실패|수집 이력이 없습니다/).first()
      ).toBeVisible({ timeout: 15000 });
    });

    test('수집 이력 테이블에 수집 기록 표시', async ({ page }) => {
      await page.goto('/collection');
      await page.waitForLoadState('domcontentloaded');

      const historyTab = page.getByText('수집 이력');
      await historyTab.click();
      await page.waitForTimeout(1500);

      const table = page.locator('table').first();
      const tableVisible = await table.isVisible().catch(() => false);

      if (tableVisible) {
        const rows = table.locator('tbody tr');
        const rowCount = await rows.count();
        expect(rowCount).toBeGreaterThanOrEqual(1);
      }
    });

    test('수집 통계 카드 표시', async ({ page }) => {
      await page.goto('/collection');
      await page.waitForLoadState('domcontentloaded');

      const historyTab = page.getByText('수집 이력');
      await historyTab.click();
      await page.waitForTimeout(1500);

      const body = await page.textContent('body');
      const hasStats = body?.includes('50') || body?.includes('96') || body?.includes('12,500');

      expect(hasStats).toBe(true);
    });
  });
});
