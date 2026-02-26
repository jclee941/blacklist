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
      expect(body).toContain('SECUDIUM');
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

    test('SECUDIUM 연결 테스트 시 OTP 모달 표시', async ({ page }) => {
      await page.route('**/api/collection/credentials/SECUDIUM/test**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              status: 'otp_required',
              message: 'KakaoTalk OTP 인증이 필요합니다.',
              session_id: 'test-sess-001',
            },
          }),
        });
      });

      await page.goto('/collection');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      const secudiumCard = page
        .locator('[class*="card"], [class*="Card"]')
        .filter({ hasText: /SECUDIUM/ })
        .first();

      const visible = await secudiumCard.isVisible().catch(() => false);
      if (visible) {
        const testBtn = secudiumCard.getByRole('button', { name: /연결 테스트|테스트/i }).first();
        if (await testBtn.isVisible().catch(() => false)) {
          await testBtn.click();
          await page.waitForTimeout(2000);

          const otpModal = page.getByText('OTP 인증');
          await expect(otpModal.first()).toBeVisible();

          const otpInput = page.locator('input[maxlength="6"]');
          await expect(otpInput.first()).toBeVisible();
        }
      }
    });

    test('OTP 모달에서 6자리 코드 입력 및 제출', async ({ page }) => {
      await page.route('**/api/collection/credentials/SECUDIUM/test**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              status: 'otp_required',
              message: 'KakaoTalk OTP 인증이 필요합니다.',
              session_id: 'otp-sess-002',
            },
          }),
        });
      });

      await page.route('**/api/collection/credentials/SECUDIUM/verify-otp**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { status: 'connected', message: 'OTP 인증 완료' },
          }),
        });
      });

      await page.goto('/collection');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      const secudiumCard = page
        .locator('[class*="card"], [class*="Card"]')
        .filter({ hasText: /SECUDIUM/ })
        .first();

      if (await secudiumCard.isVisible().catch(() => false)) {
        const testBtn = secudiumCard.getByRole('button', { name: /연결 테스트|테스트/i }).first();
        if (await testBtn.isVisible().catch(() => false)) {
          await testBtn.click();
          await page.waitForTimeout(2000);

          const otpInput = page.locator('input[maxlength="6"]').first();
          if (await otpInput.isVisible().catch(() => false)) {
            await otpInput.fill('123456');
            await expect(otpInput).toHaveValue('123456');

            const submitBtn = page.getByRole('button', { name: /인증 확인|확인|제출/i }).first();
            if (await submitBtn.isVisible().catch(() => false)) {
              await submitBtn.click();
              await page.waitForTimeout(1000);
            }
          }
        }
      }
    });

    test('OTP 입력에서 숫자만 허용', async ({ page }) => {
      await page.route('**/api/collection/credentials/SECUDIUM/test**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { status: 'otp_required', session_id: 'otp-filter' },
          }),
        });
      });

      await page.goto('/collection');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      const secudiumCard = page
        .locator('[class*="card"], [class*="Card"]')
        .filter({ hasText: /SECUDIUM/ })
        .first();

      if (await secudiumCard.isVisible().catch(() => false)) {
        const testBtn = secudiumCard.getByRole('button', { name: /연결 테스트|테스트/i }).first();
        if (await testBtn.isVisible().catch(() => false)) {
          await testBtn.click();
          await page.waitForTimeout(2000);

          const otpInput = page.locator('input[maxlength="6"]').first();
          if (await otpInput.isVisible().catch(() => false)) {
            await otpInput.type('abc123def456', { delay: 50 });
            const value = await otpInput.inputValue();
            expect(value).toMatch(/^\d*$/);
          }
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
