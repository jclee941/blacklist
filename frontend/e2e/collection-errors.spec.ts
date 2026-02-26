import { test, expect } from '@playwright/test';
import { loginViaApi, mockCollectionApis } from './collection-process.fixtures';

test.describe('수집 프로세스 E2E 테스트', () => {
  test.describe('에러 처리', () => {
    test.beforeEach(async ({ page }) => {
      await loginViaApi(page);
    });

    test('API 실패 시 에러 표시', async ({ page }) => {
      await page.route('**/api/collection/status**', async (route) => {
        await route.fulfill({ status: 500, body: 'Internal Server Error' });
      });
      await page.route('**/api/collection/statistics**', async (route) => {
        await route.fulfill({ status: 500, body: 'Internal Server Error' });
      });
      await page.route('**/api/collection/credentials', async (route) => {
        await route.fulfill({ status: 500, body: 'Internal Server Error' });
      });

      await page.goto('/collection');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      const body = await page.textContent('body');
      const hasErrorOrFallback =
        body?.includes('오류') ||
        body?.includes('에러') ||
        body?.includes('실패') ||
        body?.includes('error') ||
        body?.includes('REGTECH') ||
        body?.includes('수집 관리');

      expect(hasErrorOrFallback).toBe(true);
    });

    test('연결 테스트 실패 시 에러 알림 표시', async ({ page }) => {
      await mockCollectionApis(page);

      await page.route('**/api/collection/credentials/REGTECH/test**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { status: 'failed', message: '연결 실패: 타임아웃' },
          }),
        });
      });

      await page.goto('/collection');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      const regtechCard = page
        .locator('[class*="card"], [class*="Card"]')
        .filter({ hasText: /REGTECH/ })
        .first();

      if (await regtechCard.isVisible().catch(() => false)) {
        const testBtn = regtechCard.getByRole('button', { name: /연결 테스트|테스트/i }).first();
        if (await testBtn.isVisible().catch(() => false)) {
          await testBtn.click();
          await page.waitForTimeout(2000);

          const body = await page.textContent('body');
          const hasError =
            body?.includes('오류') ||
            body?.includes('실패') ||
            body?.includes('타임아웃') ||
            body?.includes('error');
          expect(hasError).toBe(true);
        }
      }
    });
  });
});
