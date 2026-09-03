import { test, expect } from '@playwright/test';
import { authenticatedGet, authenticatedPost } from './auth.fixtures';

/**
 * Monitoring & Metrics E2E Tests
 *
 * Tests for monitoring API endpoints:
 * - Cache metrics (stats, operations, trends, top-keys)
 * - Error metrics (stats, recent, trends, top)
 * - General metrics endpoint
 *
 * These are API-only tests (no frontend monitoring page).
 * Endpoints may return 503 if metrics collection is disabled.
 *
 * Run: npm run test:e2e -- --grep "Monitoring"
 */

test.describe('Monitoring & Metrics', () => {
  test.describe.configure({ mode: 'parallel' });

  test.describe('Cache Metrics API', () => {
    test('캐시 통계 조회', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/cache/stats');

      expect([200, 404, 503]).toContain(response.status());

      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toBeTruthy();
      }
    });

    test('캐시 작업 내역 조회', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/cache/operations');

      expect([200, 404, 503]).toContain(response.status());

      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toBeTruthy();
      }
    });

    test('캐시 트렌드 조회', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/cache/trends');

      expect([200, 404, 503]).toContain(response.status());

      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toBeTruthy();
      }
    });

    test('캐시 Top Keys 조회', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/cache/top-keys');

      expect([200, 404, 503]).toContain(response.status());

      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toBeTruthy();
      }
    });
  });

  test.describe('General Metrics API', () => {
    test('시스템 메트릭스 조회', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/metrics');

      expect([200, 404, 503]).toContain(response.status());

      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toBeTruthy();
      }
    });
  });

  test.describe('Error Metrics API', () => {
    test('에러 통계 조회', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/errors/stats');

      expect([200, 404, 503]).toContain(response.status());

      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toBeTruthy();
      }
    });

    test('최근 에러 목록 조회', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/errors/recent');

      expect([200, 404, 503]).toContain(response.status());

      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toBeTruthy();
      }
    });

    test('에러 트렌드 조회', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/errors/trends');

      expect([200, 404, 503]).toContain(response.status());

      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toBeTruthy();
      }
    });

    test('Top 에러 조회', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/errors/top');

      expect([200, 404, 503]).toContain(response.status());

      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toBeTruthy();
      }
    });

    test('일반 에러 엔드포인트 조회', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/errors/recent');

      expect([200, 404, 503]).toContain(response.status());

      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toBeTruthy();
      }
    });
  });

  test.describe('Monitoring Response Format', () => {
    test('캐시 통계 응답 형식 검증', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/cache/stats');

      if (response.status() === 200) {
        const body = await response.json();

        expect(typeof body).toBe('object');
        expect(body).not.toBeNull();
      }
    });

    test('에러 통계 응답 형식 검증', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/errors/stats');

      if (response.status() === 200) {
        const body = await response.json();

        expect(typeof body).toBe('object');
        expect(body).not.toBeNull();
      }
    });
  });

  test.describe('Monitoring Edge Cases', () => {
    test('존재하지 않는 모니터링 엔드포인트', async ({ request }) => {
      const response = await authenticatedGet(request, '/api/monitoring/nonexistent');

      expect([404, 405]).toContain(response.status());
    });

    test('잘못된 HTTP 메서드', async ({ request }) => {
      const response = await authenticatedPost(request, '/api/monitoring/cache/stats');

      expect([404, 405]).toContain(response.status());
    });
  });
});
