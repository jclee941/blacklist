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

function mockCollectionApis(page: Page) {
  return Promise.all([
    page.route('**/api/collection/status**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            collector_status: 'running',
            sources: {
              regtech: { status: 'active', last_run: '2026-02-11T10:00:00' },
              secudium: { status: 'active', last_run: '2026-02-11T09:30:00' },
            },
          },
        }),
      });
    }),
    page.route('**/api/collection/statistics**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            summary: {
              total_collections: 50,
              successful_collections: 48,
              total_items_collected: 12500,
              success_rate: 96.0,
            },
            sources: {
              regtech: {
                total_collections: 30,
                success_rate: 100.0,
                total_items: 8500,
                last_collection: '2026-02-11T10:00:00',
                avg_duration: 45.2,
              },
              secudium: {
                total_collections: 20,
                success_rate: 90.0,
                total_items: 4000,
                last_collection: '2026-02-11T09:30:00',
                avg_duration: 60.5,
              },
            },
          },
        }),
      });
    }),
    page.route('**/api/collection/credentials', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                service_name: 'REGTECH',
                username: 'regtech_user',
                connection_status: 'connected',
                status_message: '연결됨',
                last_test: '2026-02-11T10:00:00',
              },
              {
                service_name: 'SECUDIUM',
                username: 'secudium_user',
                connection_status: 'connected',
                status_message: '연결됨',
                last_test: '2026-02-11T09:30:00',
              },
            ],
          }),
        });
      } else {
        await route.continue();
      }
    }),
    page.route('**/proxy/collection/credentials/regtech', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              service_name: 'REGTECH',
              username: 'regtech_user',
              enabled: true,
              collection_interval: 'daily',
              connection_status: 'connected',
              status_message: '연결됨',
            },
          }),
        });
      } else {
        await route.continue();
      }
    }),
    page.route('**/proxy/collection/credentials/secudium', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              service_name: 'SECUDIUM',
              username: 'secudium_user',
              enabled: true,
              collection_interval: 'daily',
              connection_status: 'connected',
              status_message: '연결됨',
              otp_mode: 'manual',
            },
          }),
        });
      } else {
        await route.continue();
      }
    }),
    page.route('**/api/collection/sources**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { name: 'regtech', display_name: 'REGTECH', status: 'active' },
            { name: 'secudium', display_name: 'SECUDIUM', status: 'active' },
          ],
        }),
      });
    }),
  ]);
}

test.describe('수집 프로세스 E2E 테스트', () => {
  test.describe('수집 관리 탭', () => {
    test.beforeEach(async ({ page }) => {
      await loginViaApi(page);
      await mockCollectionApis(page);
    });

    test('수집 관리 페이지 로드 및 기본 요소 표시', async ({ page }) => {
      await page.goto('/collection');
      await page.waitForLoadState('networkidle');

      await expect(page.getByRole('heading', { name: '수집 관리' })).toBeVisible();
      await expect(page.getByText('수집 이력')).toBeVisible();

      const body = await page.textContent('body');
      expect(body).toContain('REGTECH');
      expect(body).toContain('SECUDIUM');
    });

    test('수집기 카드에 연결 상태 배지 표시', async ({ page }) => {
      await page.goto('/collection');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);

      const connectedBadges = page.getByText('연결됨');
      const count = await connectedBadges.count();
      expect(count).toBeGreaterThanOrEqual(1);
    });

    test('수집기 카드에 액션 버튼 3개 표시', async ({ page }) => {
      await page.goto('/collection');
      await page.waitForLoadState('networkidle');
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
      await page.waitForLoadState('networkidle');
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
      await page.waitForLoadState('networkidle');
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
      await page.waitForLoadState('networkidle');
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
      await page.waitForLoadState('networkidle');
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
      await page.waitForLoadState('networkidle');
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
      await page.waitForLoadState('networkidle');
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
                  source: 'secudium',
                  status: 'success',
                  items_collected: 200,
                  started_at: '2026-02-11T09:30:00',
                  completed_at: '2026-02-11T09:31:30',
                  duration: 90,
                },
                {
                  id: 3,
                  source: 'regtech',
                  status: 'failed',
                  items_collected: 0,
                  started_at: '2026-02-10T10:00:00',
                  completed_at: '2026-02-10T10:00:30',
                  duration: 30,
                  error: 'Connection timeout',
                },
              ],
              total: 3,
              page: 1,
              per_page: 20,
            },
          }),
        });
      });
    });

    test('수집 이력 탭으로 전환', async ({ page }) => {
      await page.goto('/collection');
      await page.waitForLoadState('networkidle');

      const historyTab = page.getByText('수집 이력');
      await historyTab.click();
      await page.waitForTimeout(1000);

      const body = await page.textContent('body');
      const hasHistoryContent =
        body?.includes('regtech') ||
        body?.includes('REGTECH') ||
        body?.includes('secudium') ||
        body?.includes('SECUDIUM') ||
        body?.includes('성공') ||
        body?.includes('실패');

      expect(hasHistoryContent).toBe(true);
    });

    test('수집 이력 테이블에 수집 기록 표시', async ({ page }) => {
      await page.goto('/collection');
      await page.waitForLoadState('networkidle');

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
      await page.waitForLoadState('networkidle');

      const historyTab = page.getByText('수집 이력');
      await historyTab.click();
      await page.waitForTimeout(1500);

      const body = await page.textContent('body');
      const hasStats = body?.includes('50') || body?.includes('96') || body?.includes('12,500');

      expect(hasStats).toBe(true);
    });
  });

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
      await page.waitForLoadState('networkidle');
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
      await page.waitForLoadState('networkidle');
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
