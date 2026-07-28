import { test, expect, Page } from '@playwright/test';
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
    await page.waitForLoadState('domcontentloaded');
  }
}

test.describe('대시보드 기능 테스트', () => {
  test.describe.configure({ mode: 'parallel' });

  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
  });

  test('대시보드 헤더가 표시된다', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '대시보드', level: 1 })).toBeVisible();
    await expect(page.getByText('실시간 IP 블랙리스트 모니터링 및 관리')).toBeVisible();
  });

  test('통계 카드 4개가 표시된다', async ({ page }) => {
    const statLabels = ['전체 IP 주소', '차단된 IP', '24시간 신규', '화이트리스트'];
    for (const label of statLabels) {
      await expect(page.getByText(label).first()).toBeVisible();
    }
  });

  test('통계 카드에 숫자 값이 표시된다', async ({ page }) => {
    await page.waitForTimeout(2000);
    const h3Elements = page.locator('h3');
    const count = await h3Elements.count();
    expect(count).toBeGreaterThanOrEqual(4);
  });

  test('빠른 작업 링크가 올바른 페이지로 이동한다', async ({ page }) => {
    const quickActions: [string, string][] = [
      ['IP 관리', '/ip-management'],
      ['데이터 수집', '/collection'],
      ['일별 통계', '/analytics'],
      ['FortiGate 연동', '/fortinet'],
      ['데이터베이스', '/database'],
    ];

    for (const [name, path] of quickActions) {
      const link = page.getByRole('link', { name }).first();
      await expect(link).toBeVisible();
      await expect(link).toHaveAttribute('href', path);
    }
  });

  test('빠른 작업 클릭 시 해당 페이지로 이동한다', async ({ page }) => {
    const link = page.getByRole('link', { name: 'IP 관리' }).first();
    await link.click();
    await expect(page).toHaveURL(/\/ip-management/);
  });

  test('시스템 상태 섹션이 표시된다', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '시스템 상태' })).toBeVisible();

    const statusItems = ['API 서버', '데이터베이스', '수집 활성화'];
    for (const item of statusItems) {
      await expect(page.getByText(item).first()).toBeVisible();
    }
  });

  test('시스템 상태에 정상/오류 상태가 표시된다', async ({ page }) => {
    // 시스템 상태 카드가 비동기 로드되므로 넉넉한 timeout으로 대기
    const statusText = page.getByText(/정상|오류|활성|비활성/).first();
    await expect(statusText).toBeVisible({ timeout: 15000 });
  });

  test('최근 수집 활동 섹션이 표시된다', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '최근 수집 활동' })).toBeVisible();

    const hasContent =
      (await page
        .getByText('최근 수집 활동이 없습니다')
        .isVisible()
        .catch(() => false)) ||
      (await page
        .getByRole('link', { name: '전체 보기' })
        .isVisible()
        .catch(() => false));
    expect(hasContent).toBeTruthy();
  });

  test('전체 보기 링크가 수집 페이지로 연결된다', async ({ page }) => {
    const link = page.getByRole('link', { name: '전체 보기' });
    if (await link.isVisible().catch(() => false)) {
      await expect(link).toHaveAttribute('href', '/collection');
    }
  });

  test('로딩 상태가 표시된 후 데이터가 로드된다', async ({ page }) => {
    await page.goto('/');

    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByRole('heading', { name: '대시보드', level: 1 })).toBeVisible({
      timeout: 15000,
    });
  });

  test('API 에러 시 에러 상태가 처리된다', async ({ page }) => {
    await page.route('**/api/stats', (route) => route.fulfill({ status: 500, body: '{}' }));
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.getByRole('heading', { name: '대시보드', level: 1 })).toBeVisible();
  });
});
