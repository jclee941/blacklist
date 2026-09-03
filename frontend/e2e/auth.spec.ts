import { test, expect } from '@playwright/test';
import { getE2ECredentials, getSharedAuthToken, loginViaApi } from './auth.fixtures';

test.describe.configure({ mode: 'serial', retries: 0 });

const SENTINEL_CREDENTIALS = {
  username: '__SET_ADMIN_USERNAME__',
  password: '__SET_ADMIN_PASSWORD__',
} as const;

test.describe('인증 - API 로그인', () => {
  test('전역 로그인에서 유효한 토큰을 발급받는다', () => {
    const token = getSharedAuthToken();
    expect(token.length).toBeGreaterThan(0);
  });

  test('잘못된 자격증명으로 로그인 실패', async ({ page }) => {
    const response = await page.request.post(`/api/auth/login`, {
      data: { username: 'wrong', password: 'wrong' },
    });
    expect(response.status()).toBe(401);
  });

  test('빈 자격증명으로 로그인 실패', async ({ page }) => {
    const response = await page.request.post(`/api/auth/login`, {
      data: { username: '', password: '' },
    });
    expect(response.status()).toBe(400);
  });

  test('공개된 센티널 자격증명으로 로그인 실패', async ({ page }) => {
    const response = await page.request.post('/api/auth/login', {
      data: SENTINEL_CREDENTIALS,
    });

    expect(response.status()).toBe(401);
  });
});

test.describe('인증 - 토큰 기반 접근', () => {
  test('토큰으로 보호된 API 접근 성공', async ({ page }) => {
    const token = getSharedAuthToken();
    const response = await page.request.get(`/api/auth/verify`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(response.status()).toBe(200);
    await expect(response.json()).resolves.toMatchObject({ valid: true });
  });

  test('토큰 없이 보호된 API 접근 실패', async ({ page }) => {
    const identityResponse = await page.request.get(`/api/auth/me`);
    const dashboardResponse = await page.request.get('/api/web-stats');

    expect(identityResponse.status()).toBe(401);
    expect(dashboardResponse.status()).toBe(401);
  });

  test('잘못된 토큰으로 API 접근 실패', async ({ page }) => {
    const response = await page.request.get(`/api/auth/me`, {
      headers: { Authorization: 'Bearer invalid-token-12345' },
    });
    expect(response.status()).toBe(401);
  });

  test('토큰 검증 API 정상 동작', async ({ page }) => {
    const token = getSharedAuthToken();
    const response = await page.request.get(`/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    expect(response.status()).toBe(200);
    await expect(response.json()).resolves.toMatchObject({ role: 'admin' });
  });
});

test.describe('인증 - 공개 엔드포인트', () => {
  test('헬스체크 엔드포인트 토큰 불필요', async ({ page }) => {
    const response = await page.request.get('/health');
    expect(response.status()).toBe(200);
  });

  test('FortiGate threat-feed 공개 접근', async ({ page }) => {
    const response = await page.request.get(`/api/fortinet/threat-feed`);
    expect(response.status()).not.toBe(401);
  });
});

test.describe('인증 - 토큰 지속성', () => {
  test('미인증 사용자를 로그인 페이지로 이동', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveURL(/\/login$/);
  });

  test('로그인 화면에서 인증 후 대시보드로 이동', async ({ page }) => {
    const credentials = getE2ECredentials();
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('관리자 아이디').fill(credentials.username);
    await page.getByLabel('비밀번호').fill(credentials.password);
    const loginResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith('/api/auth/login') && response.request().method() === 'POST'
    );
    await page.getByRole('button', { name: '로그인' }).click();

    expect((await loginResponse).status()).toBe(200);
    await expect(page).toHaveURL(/\/$/, { timeout: 30000 });
    await expect
      .poll(() => page.evaluate(() => localStorage.getItem('blacklist_auth_token')))
      .not.toBeNull();
  });

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
    await page.reload();

    const response = await page.request.get(`/api/auth/me`);
    expect(response.status()).toBe(401);
    await expect(page).toHaveURL(/\/login$/);
  });

  test('로그아웃 시 토큰 삭제 후 로그인 화면으로 이동', async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/');

    await page.getByRole('button', { name: '로그아웃' }).click();

    await expect(page).toHaveURL(/\/login$/);
    await expect
      .poll(() => page.evaluate(() => localStorage.getItem('blacklist_auth_token')))
      .toBeNull();
  });
});
