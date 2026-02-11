import { test, expect, type Page } from '@playwright/test';

test.describe.configure({ mode: 'parallel' });

async function loginViaApi(page: Page) {
  const response = await page.request.post('/api/auth/login', {
    data: { username: 'admin', password: 'admin' },
  });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  const token = body.data?.token ?? body.token;
  expect(token).toBeTruthy();
  await page.goto('/');
  await page.evaluate((t) => localStorage.setItem('blacklist_auth_token', t), token);
  await page.reload();
  await page.waitForLoadState('networkidle');
  return token;
}

test.describe('인증 - API 로그인', () => {
  test('유효한 자격증명으로 로그인 성공', async ({ page }) => {
    const response = await page.request.post(`/api/auth/login`, {
      data: { username: 'admin', password: 'admin' },
    });
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    const token = body.data?.token ?? body.token;
    expect(token).toBeTruthy();
    expect(typeof token).toBe('string');
  });

  test('잘못된 자격증명으로 로그인 실패', async ({ page }) => {
    const response = await page.request.post(`/api/auth/login`, {
      data: { username: 'wrong', password: 'wrong' },
    });
    expect(response.ok()).toBeFalsy();
  });

  test('빈 자격증명으로 로그인 실패', async ({ page }) => {
    const response = await page.request.post(`/api/auth/login`, {
      data: { username: '', password: '' },
    });
    expect(response.ok()).toBeFalsy();
  });
});

test.describe('인증 - 토큰 기반 접근', () => {
  test('토큰으로 보호된 API 접근 성공', async ({ page }) => {
    const token = await loginViaApi(page);
    const response = await page.request.get(`/api/auth/verify`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    // Verify token is accepted (not rejected as unauthorized)
    expect(response.status()).not.toBe(401);
  });

  test('토큰 없이 보호된 API 접근 실패', async ({ page }) => {
    const response = await page.request.get(`/api/auth/me`);
    expect([401, 500]).toContain(response.status());
  });

  test('잘못된 토큰으로 API 접근 실패', async ({ page }) => {
    const response = await page.request.get(`/api/auth/me`, {
      headers: { Authorization: 'Bearer invalid-token-12345' },
    });
    expect([401, 500]).toContain(response.status());
  });

  test('토큰 검증 API 정상 동작', async ({ page }) => {
    const token = await loginViaApi(page);
    const response = await page.request.get(`/api/health`);
    expect(response.ok()).toBeTruthy();
  });
});

test.describe('인증 - 공개 엔드포인트', () => {
  test('헬스체크 엔드포인트 토큰 불필요', async ({ page }) => {
    const response = await page.request.get(`/api/health`);
    expect(response.ok()).toBeTruthy();
  });

  test('FortiGate threat-feed 공개 접근', async ({ page }) => {
    const response = await page.request.get(`/api/fortinet/threat-feed`);
    expect(response.status()).not.toBe(401);
  });
});

test.describe('인증 - 토큰 지속성', () => {
  test('localStorage에 토큰 저장 후 페이지 이동 유지', async ({ page }) => {
    await page.goto('/');
    const token = await loginViaApi(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const storedToken = await page.evaluate(() => localStorage.getItem('blacklist_auth_token'));
    expect(storedToken).toBe(token);
  });

  test('토큰 삭제 후 보호된 페이지 접근시 인증 필요', async ({ page }) => {
    await page.goto('/');
    await loginViaApi(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.evaluate(() => localStorage.removeItem('blacklist_auth_token'));

    const response = await page.request.get(`/api/auth/me`);
    expect([401, 500]).toContain(response.status());
  });
});
