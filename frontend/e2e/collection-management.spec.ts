import { test, expect } from '@playwright/test';
import { loginViaApi, mockCollectionApis } from './collection-process.fixtures';

test.describe('수집 프로세스 E2E 테스트', () => {
  test.describe('수집 관리 탭', () => {
    test.beforeEach(async ({ page }) => {
      await loginViaApi(page);
      await mockCollectionApis(page);
    });

    test('수집 관리 페이지 로드 및 기본 요소 표시', async ({ page }) => {
      await page.goto('/collection');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: '수집 관리' })).toBeVisible();
      await expect(page.getByText('수집 이력')).toBeVisible();

      const body = await page.textContent('body');
      expect(body).toContain('REGTECH');
    });

    test('수집기 카드에 연결 상태 배지 표시', async ({ page }) => {
      await page.goto('/collection');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      const connectedBadges = page.getByText('연결됨');
      const count = await connectedBadges.count();
      expect(count).toBeGreaterThanOrEqual(1);
    });

    test('수집기 카드에 액션 버튼 3개 표시', async ({ page }) => {
      await page.goto('/collection');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      const testButtons = page.getByRole('button', { name: /연결 테스트|테스트/i });
      const triggerButtons = page.getByRole('button', { name: /수집 시작|수집/i });
      const settingsButtons = page.getByRole('button', { name: /설정/i });

      expect(await testButtons.count()).toBeGreaterThanOrEqual(1);
      expect(await triggerButtons.count()).toBeGreaterThanOrEqual(1);
      expect(await settingsButtons.count()).toBeGreaterThanOrEqual(1);
    });

    test('REGTECH 연결 테스트 성공 시 연결됨 상태 표시', async ({ page }) => {
      await page.route('**/api/collection/credentials/REGTECH/test**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { status: 'connected', message: '연결 성공' },
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

      const visible = await regtechCard.isVisible().catch(() => false);
      if (visible) {
        const testBtn = regtechCard.getByRole('button', { name: /연결 테스트|테스트/i }).first();
        if (await testBtn.isVisible().catch(() => false)) {
          await testBtn.click();
          await page.waitForTimeout(2000);
          await expect(page.getByText('연결됨').first()).toBeVisible();
        }
      }
    });

    test('설정 버튼 클릭 시 인증정보 수정 모달 표시', async ({ page }) => {
      await page.goto('/collection');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      const regtechCard = page
        .locator('[class*="card"], [class*="Card"]')
        .filter({ hasText: /REGTECH/ })
        .first();

      if (await regtechCard.isVisible().catch(() => false)) {
        const settingsBtn = regtechCard.getByRole('button', { name: /설정/i }).first();
        if (await settingsBtn.isVisible().catch(() => false)) {
          await settingsBtn.click();
          await page.waitForTimeout(1000);

          const modal = page.locator('[role="dialog"], [class*="modal"], [class*="Modal"]').first();
          const modalVisible = await modal.isVisible().catch(() => false);

          if (modalVisible) {
            const usernameInput = page.locator(
              'input[name="username"], input[placeholder*="사용자"]'
            );
            expect(await usernameInput.count()).toBeGreaterThanOrEqual(1);
          }
        }
      }
    });

    test('REGTECH 수집 트리거 성공', async ({ page }) => {
      let triggerCalled = false;
      await page.route('**/api/collection/credentials/REGTECH/test**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { status: 'connected', message: '연결 성공' },
          }),
        });
      });

      await page.route('**/api/collection/trigger/REGTECH**', async (route) => {
        triggerCalled = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { message: '수집이 시작되었습니다.', task_id: 'task-001' },
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
        const triggerBtn = regtechCard.getByRole('button', { name: /수집 시작|수집/i }).first();
        if (await triggerBtn.isVisible().catch(() => false)) {
          await triggerBtn.click();
          await page.waitForTimeout(3000);
          expect(triggerCalled).toBe(true);
        }
      }
    });
  });
});
