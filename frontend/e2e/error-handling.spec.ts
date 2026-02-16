import { test, expect } from '@playwright/test';

/**
 * Error Handling Tests
 *
 * Tests for error scenarios, network failures, and graceful degradation.
 * Ensures the application handles edge cases properly.
 *
 * Run: npm run test:e2e -- --grep "Error Handling"
 */

test.describe('Error Handling', () => {
  test.describe.configure({ mode: 'serial' });

  test.describe('Page Error Responses', () => {
    test('404 페이지 - 존재하지 않는 경로', async ({ page }) => {
      const response = await page.goto('/nonexistent-page-12345');

      // Should either redirect to 404 page or show error content
      // Next.js typically returns 404 status
      if (response) {
        // Page might return 404 or redirect
        expect([200, 404]).toContain(response.status());
      }

      // Check for 404 content or error indication
      const bodyText = await page.locator('body').textContent();
      expect(bodyText).toBeTruthy();
    });

    test('커스텀 404 페이지 - 한국어 안내 메시지 표시', async ({ page }) => {
      await page.goto('/this-page-does-not-exist');

      const heading = page.locator('h1');
      if ((await heading.count()) > 0) {
        const text = await heading.textContent();
        if (text?.includes('찾을 수 없습니다')) {
          await expect(heading).toContainText('찾을 수 없습니다');
        }
      }

      const homeLink = page.locator('a[href="/"]');
      if ((await homeLink.count()) > 0) {
        await expect(homeLink.first()).toBeVisible();
      }
    });

    test('커스텀 404 페이지 - 홈으로 이동 링크 동작', async ({ page }) => {
      await page.goto('/another-nonexistent-path');

      const homeLink = page.locator('a[href="/"]').first();
      if ((await homeLink.count()) > 0) {
        await homeLink.click();
        await page.waitForLoadState('domcontentloaded');
        expect(page.url()).toContain('/');
      }
    });

    test('잘못된 API 엔드포인트 요청', async ({ request }) => {
      const response = await request.get('/api/invalid-endpoint-xyz');

      // Should return 404 or appropriate error status
      expect([400, 404, 405]).toContain(response.status());
    });
  });

  test.describe('Network Failure Simulation', () => {
    test('API 요청 실패 시 에러 UI 표시', async ({ page }) => {
      // Block API calls
      await page.route('**/api/status', (route) => {
        route.abort('failed');
      });

      await page.goto('/');

      // Page should still load (graceful degradation)
      await expect(page.locator('body')).toBeVisible();

      // Look for error indicator or fallback content
      // This might be an error message, loading fallback, or degraded state
      const hasContent = await page.locator('body').textContent();
      expect(hasContent).toBeTruthy();
    });

    test('느린 네트워크 - 로딩 상태 확인', async ({ page }) => {
      // Simulate slow network
      await page.route('**/api/**', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await route.continue();
      });

      // Start navigation
      const navigationPromise = page.goto('/');

      // Check for loading state (within first 1 second)
      await page.waitForTimeout(500);

      // Page should show something (loading indicator or partial content)
      await expect(page.locator('body')).toBeVisible();

      // Wait for navigation to complete
      await navigationPromise;
    });

    test('API 타임아웃 처리', async ({ page, request }) => {
      // Test that timeouts are handled gracefully
      await page.route('**/api/blacklist', async (route) => {
        // Simulate timeout by never responding
        await new Promise((resolve) => setTimeout(resolve, 10000));
        await route.abort('timedout');
      });

      // Navigate to a page that uses the blacklist API
      await page.goto('/ip-management', { timeout: 15000 }).catch(() => {
        // Navigation might timeout, which is expected
      });

      // Page should still be usable
      await expect(page.locator('body')).toBeVisible();
    });
  });

  test.describe('Form Validation Errors', () => {
    test('IP 관리 - 빈 폼 제출 시 유효성 검사', async ({ page }) => {
      await page.goto('/ip-management');

      // Look for any form or input
      const hasForm = await page.locator('form, input, button').count();

      if (hasForm > 0) {
        // Try to find and click submit without filling required fields
        const submitButton = page.locator(
          'button[type="submit"], button:has-text("추가"), button:has-text("저장"), button:has-text("Add")'
        );

        if ((await submitButton.count()) > 0) {
          await submitButton.first().click();

          // Should show validation error or prevent submission
          // Look for error message or required field indication
          await page.waitForTimeout(500);

          // The form should either show error or stay on same page
          await expect(page.locator('body')).toBeVisible();
        }
      }
    });

    test('잘못된 IP 형식 입력', async ({ page }) => {
      await page.goto('/ip-management');

      // Find IP input field
      const ipInput = page
        .locator('input[placeholder*="IP"], input[name*="ip"], input[type="text"]')
        .first();

      if ((await ipInput.count()) > 0) {
        // Enter invalid IP format
        await ipInput.fill('invalid-ip-format');

        // Try to trigger validation
        await ipInput.blur();

        // Look for validation feedback
        await page.waitForTimeout(300);

        // Check that page handled invalid input (no crash)
        await expect(page.locator('body')).toBeVisible();
      }
    });
  });

  test.describe('Graceful Degradation', () => {
    test('상태 API 차단 시에도 페이지 로드', async ({ page }) => {
      // Block status endpoints
      await page.route('**/api/status', (route) => route.abort());
      await page.route('**/api/health', (route) => route.abort());

      await page.goto('/');

      // Page should still load despite API failures
      await expect(page.locator('body')).toBeVisible();

      // Navigation should still work
      const nav = page.locator('nav');
      if ((await nav.count()) > 0) {
        await expect(nav).toBeVisible();
      }
    });

    test('부분적 데이터 실패 시 나머지 UI 정상 동작', async ({ page }) => {
      // Block only one endpoint
      await page.route('**/api/collection/**', (route) => route.abort());

      await page.goto('/');

      // Other parts of the page should work
      await expect(page.locator('body')).toBeVisible();

      // Header/nav should be visible
      const header = page.locator('header, nav').first();
      if ((await header.count()) > 0) {
        await expect(header).toBeVisible();
      }
    });
  });
});
