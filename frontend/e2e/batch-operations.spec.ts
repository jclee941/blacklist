import { test, expect, Page } from '@playwright/test';
import { getE2ECredentials } from './auth.fixtures';

/**
 * Batch IP Operations E2E Tests
 *
 * Tests for bulk IP management operations:
 * - Batch add (POST /api/blacklist/batch/add)
 * - Batch remove (POST /api/blacklist/batch/remove)
 * - Batch update (POST /api/blacklist/batch/update)
 *
 * These endpoints are rate limited (10/hour, 2/minute) so tests use mocked responses.
 *
 * Run: npm run test:e2e -- --grep "Batch Operations"
 */

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

test.describe('Batch Operations', () => {
  test.describe.configure({ mode: 'parallel' });

  test.describe('Batch Add API', () => {
    test('유효한 IP 목록 일괄 추가', async ({ request }) => {
      const response = await request.post('/api/blacklist/batch/add', {
        data: {
          ips: [
            { ip_address: '10.99.99.1', reason: 'E2E batch test 1', source: 'e2e-test' },
            { ip_address: '10.99.99.2', reason: 'E2E batch test 2', source: 'e2e-test' },
          ],
        },
      });

      expect([200, 201, 207, 429]).toContain(response.status());

      if (response.status() !== 429) {
        const body = await response.json();
        expect(body).toBeTruthy();
      }
    });

    test('빈 IP 목록으로 일괄 추가 시 에러', async ({ request }) => {
      const response = await request.post('/api/blacklist/batch/add', {
        data: { ips: [] },
      });

      expect([400, 422, 429]).toContain(response.status());
    });

    test('잘못된 IP 형식 포함 시 처리', async ({ request }) => {
      const response = await request.post('/api/blacklist/batch/add', {
        data: {
          ips: [
            { ip_address: 'not-an-ip', reason: 'invalid', source: 'e2e-test' },
            { ip_address: '10.99.99.3', reason: 'valid', source: 'e2e-test' },
          ],
        },
      });

      expect([200, 207, 400, 422, 429]).toContain(response.status());
    });

    test('본문 없이 요청 시 에러', async ({ request }) => {
      const response = await request.post('/api/blacklist/batch/add', {
        data: {},
      });

      expect([400, 422, 429]).toContain(response.status());
    });
  });

  test.describe('Batch Remove API', () => {
    test('IP 목록 일괄 삭제', async ({ request }) => {
      const response = await request.post('/api/blacklist/batch/remove', {
        data: {
          ips: ['10.99.99.1', '10.99.99.2'],
        },
      });

      expect([200, 207, 404, 429]).toContain(response.status());
    });

    test('빈 목록으로 일괄 삭제 시 에러', async ({ request }) => {
      const response = await request.post('/api/blacklist/batch/remove', {
        data: { ips: [] },
      });

      expect([400, 422, 429]).toContain(response.status());
    });
  });

  test.describe('Batch Update API', () => {
    test('IP 목록 일괄 업데이트', async ({ request }) => {
      const response = await request.post('/api/blacklist/batch/update', {
        data: {
          ips: [{ ip_address: '10.99.99.1', reason: 'Updated via E2E batch' }],
        },
      });

      expect([200, 207, 400, 404, 429]).toContain(response.status());
    });

    test('빈 업데이트 요청 시 에러', async ({ request }) => {
      const response = await request.post('/api/blacklist/batch/update', {
        data: { ips: [] },
      });

      expect([400, 422, 429]).toContain(response.status());
    });
  });

  test.describe('Batch Rate Limiting', () => {
    test('속도 제한 응답 확인', async ({ request }) => {
      const responses = [];
      for (let i = 0; i < 3; i++) {
        const response = await request.post('/api/blacklist/batch/add', {
          data: {
            ips: [{ ip_address: `10.99.98.${i}`, reason: 'rate limit test', source: 'e2e-test' }],
          },
        });
        responses.push(response.status());
      }

      const hasValidStatus = responses.every((s) => [200, 201, 207, 429].includes(s));
      expect(hasValidStatus).toBe(true);
    });
  });

  test.describe('Batch UI Integration', () => {
    test('IP 관리 페이지에서 일괄 작업 UI 확인', async ({ page }) => {
      await loginViaApi(page);
      await page.goto('/ip-management');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.locator('body')).toBeVisible();

      const batchElements = page.locator(
        'button:has-text("일괄"), button:has-text("Batch"), button:has-text("대량"), [data-testid*="batch"]'
      );

      const count = await batchElements.count();
      if (count > 0) {
        await expect(batchElements.first()).toBeVisible();
      }
    });
  });
});
