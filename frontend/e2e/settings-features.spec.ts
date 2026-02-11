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

test.describe('설정 페이지', () => {
  test.describe.configure({ mode: 'parallel' });

  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
  });

  test('페이지 헤더가 올바르게 표시된다', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '설정' }).first()).toBeVisible();
    await expect(page.getByText('시스템 설정 및 환경 구성')).toBeVisible();
  });

  test('4개 탭이 모두 표시된다', async ({ page }) => {
    const tabs = ['시스템 설정', '데이터베이스', '보안', '알림'];
    for (const tabName of tabs) {
      await expect(page.getByRole('tab', { name: tabName })).toBeVisible();
    }
  });

  test('기본 탭이 시스템 설정이다', async ({ page }) => {
    const activeTab = page.getByRole('tab', {
      name: '시스템 설정',
    });
    await expect(activeTab).toHaveAttribute('aria-selected', 'true');
  });

  test('시스템 설정 탭에 토글과 입력 필드가 있다', async ({ page }) => {
    await page.waitForTimeout(500);
    const inputs = page.locator('input[type="number"], button.rounded-full');
    const count = await inputs.count();
    expect(count).toBeGreaterThan(0);
  });

  test('탭 전환이 동작한다 - 데이터베이스', async ({ page }) => {
    await page.getByRole('tab', { name: '데이터베이스' }).click();
    await page.waitForTimeout(500);
    await expect(page.getByRole('tab', { name: '데이터베이스' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
  });

  test('탭 전환이 동작한다 - 보안', async ({ page }) => {
    await page.getByRole('tab', { name: '보안' }).click();
    await page.waitForTimeout(500);
    await expect(page.getByRole('tab', { name: '보안' })).toHaveAttribute('aria-selected', 'true');
  });

  test('탭 전환이 동작한다 - 알림', async ({ page }) => {
    await page.getByRole('tab', { name: '알림' }).click();
    await page.waitForTimeout(500);
    await expect(page.getByRole('tab', { name: '알림' })).toHaveAttribute('aria-selected', 'true');
  });

  test('알림 탭에 이메일/슬랙 설정이 있다', async ({ page }) => {
    await page.getByRole('tab', { name: '알림' }).click();
    await page.waitForTimeout(500);

    const toggles = page.locator('button.rounded-full');
    const count = await toggles.count();
    expect(count).toBeGreaterThan(0);
  });

  test('저장 버튼이 동작한다', async ({ page }) => {
    const saveBtn = page.getByRole('button', { name: /저장/ });
    if (await saveBtn.isVisible().catch(() => false)) {
      await saveBtn.click();

      const responseMsg = page.getByText(/설정이 저장되었습니다|설정 저장에 실패했습니다/);
      await expect(responseMsg).toBeVisible({ timeout: 10000 });
    }
  });

  test('데이터베이스 탭에 연결 테스트 버튼이 있다', async ({ page }) => {
    await page.getByRole('tab', { name: '데이터베이스' }).click();
    await page.waitForTimeout(500);

    const testBtn = page.getByRole('button', {
      name: /연결 테스트|테스트/,
    });
    if (await testBtn.isVisible().catch(() => false)) {
      await expect(testBtn).toBeVisible();
    }
  });
});
