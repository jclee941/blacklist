import { test, expect, type Page } from '@playwright/test';

/**
 * Smoke Tests - Deployment Verification
 *
 * Fast verification suite for post-deployment checks.
 * Target execution time: < 30 seconds
 *
 * Run: npm run test:e2e -- --grep "@smoke"
 * Run with custom URL: BASE_URL=https://staging.example.com npm run test:e2e -- --grep "@smoke"
 */

const API_BASE = process.env.API_URL || 'http://localhost:2542';

async function getToken(page: Page): Promise<string> {
  const res = await page.request.post(`${API_BASE}/api/auth/login`, {
    data: { username: 'admin', password: 'admin' },
  });
  const body = await res.json();
  return body.data?.token ?? body.token ?? '';
}

test.describe('Smoke Tests @smoke', () => {
  test.describe.configure({ mode: 'parallel' });

  test.describe('Health Endpoints', () => {
    test('GET /health - 메인 앱 헬스체크', async ({ request }) => {
      const response = await request.get('/health');
      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body).toHaveProperty('status');
    });

    test('GET /health - API 헬스체크 (direct)', async ({ page }) => {
      const res = await page.request.get(`${API_BASE}/health`);
      expect(res.status()).toBe(200);
      const body = await res.json();
      expect(body).toHaveProperty('status');
    });

    test('GET /api/collection/health - 수집기 헬스체크', async ({ page }) => {
      const token = await getToken(page);
      const res = await page.request.get(`${API_BASE}/api/collection/health`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(res.status()).toBe(200);
      const body = await res.json();
      expect(body).toHaveProperty('status');
    });

    test('GET /api/blacklist/health - 블랙리스트 서비스 헬스체크', async ({ page }) => {
      const token = await getToken(page);
      const res = await page.request.get(`${API_BASE}/api/blacklist/health`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(res.status()).toBe(200);
    });

    test('GET /api/system/status - 시스템 상태', async ({ page }) => {
      const token = await getToken(page);
      const res = await page.request.get(`${API_BASE}/api/system/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(res.status()).toBe(200);
      const body = await res.json();
      expect(body).toHaveProperty('status');
    });
  });

  test.describe('Core Pages Load', () => {
    test('Dashboard (/) 로드', async ({ page }) => {
      await page.goto('/');
      await expect(page).toHaveTitle(/Blacklist/i);
      await expect(page.locator('body')).toBeVisible();
    });

    test('IP 관리 페이지 로드', async ({ page }) => {
      await page.goto('/ip-management');
      await expect(page.locator('body')).toBeVisible();
      await expect(page.locator('h1, [data-testid="page-title"]').first()).toBeVisible();
    });

    test('수집 관리 페이지 로드', async ({ page }) => {
      await page.goto('/collection');
      await expect(page.locator('body')).toBeVisible();
    });

    test('FortiGate 페이지 로드', async ({ page }) => {
      await page.goto('/fortinet');
      await expect(page.locator('body')).toBeVisible();
    });

    test('데이터베이스 페이지 로드', async ({ page }) => {
      await page.goto('/database');
      await expect(page.locator('body')).toBeVisible();
    });
  });

  test.describe('API Basic Response', () => {
    test('GET /api/blacklist/list - 블랙리스트 데이터 응답', async ({ page }) => {
      const token = await getToken(page);
      const res = await page.request.get(`${API_BASE}/api/blacklist/list`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(res.status()).toBe(200);
      const body = await res.json();
      expect(body).toBeDefined();
      expect(typeof body === 'object').toBeTruthy();
    });

    test('GET /api/status - 상태 API 응답', async ({ page }) => {
      const token = await getToken(page);
      const res = await page.request.get(`${API_BASE}/api/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(res.status()).toBe(200);
      const body = await res.json();
      expect(body).toBeDefined();
    });
  });
});
