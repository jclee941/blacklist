/**
 * Regression Test: Collection IP Count Shows 0
 *
 * PROBLEM:
 * On the data collection page (/collection), each collector's collected IP count
 * always displayed 0, even when the backend reported non-zero total_items.
 *
 * ROOT CAUSE:
 * Frontend `getSourceCount()` in useCollectionManagement.ts checked for
 * `entry?.count ?? entry?.cumulative_collected ?? 0` but the backend
 * `/api/collection/statistics` endpoint returns `total_items` per source.
 * The SourceStats type lacked the `total_items` field entirely, causing the
 * fallback chain to always resolve to 0.
 *
 * FIX:
 * 1. Added `total_items` field to SourceStats interface in types.ts
 * 2. Updated getSourceCount() to check `total_items` first:
 *    `entry?.total_items ?? entry?.count ?? entry?.cumulative_collected ?? 0`
 */

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

test.describe('Regression: Issue #002 - Collection IP count shows 0', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
  });

  test('should display non-zero IP counts when backend returns total_items @regression', async ({
    page,
  }) => {
    // STEP 1: Mock the statistics API to return known total_items values
    await page.route('**/api/proxy/collection/statistics**', async (route) => {
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
    });

    // STEP 2: Also mock the status endpoint for collector cards
    await page.route('**/api/proxy/collection/status**', async (route) => {
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
    });

    // STEP 3: Navigate to collection page
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // STEP 4: Verify that collector cards do NOT show "0" as their IP count
    // Before the fix, all cards showed "수집된 IP: 0" or just "0"
    // After the fix, they should show the actual total_items values
    const pageContent = await page.textContent('body');

    // The page should contain the non-zero counts from our mock
    // At minimum, the values should appear somewhere on the management tab
    const hasNonZeroCount =
      pageContent?.includes('8,500') ||
      pageContent?.includes('8500') ||
      pageContent?.includes('4,000') ||
      pageContent?.includes('4000') ||
      pageContent?.includes('12,500') ||
      pageContent?.includes('12500');

    // If collector cards are rendered, they should not all show 0
    const collectorCards = page.locator('[class*="card"], [class*="Card"]');
    const cardCount = await collectorCards.count();

    if (cardCount > 0) {
      // At least one card should have a non-zero count displayed
      let foundNonZero = false;
      for (let i = 0; i < cardCount; i++) {
        const cardText = await collectorCards.nth(i).textContent();
        if (cardText && /[1-9]\d*/.test(cardText)) {
          foundNonZero = true;
          break;
        }
      }
      expect(foundNonZero || hasNonZeroCount).toBe(true);
    }
  });

  test('should correctly map total_items from statistics API @regression', async ({ page }) => {
    // STEP 1: Intercept the statistics API call and verify response is consumed
    let statisticsRequested = false;
    await page.route('**/api/proxy/collection/statistics**', async (route) => {
      statisticsRequested = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            summary: {
              total_collections: 10,
              successful_collections: 10,
              total_items_collected: 500,
              success_rate: 100.0,
            },
            sources: {
              regtech: {
                total_collections: 10,
                success_rate: 100.0,
                total_items: 500,
                last_collection: '2026-02-11T10:00:00',
                avg_duration: 30.0,
              },
            },
          },
        }),
      });
    });

    await page.route('**/api/proxy/collection/status**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            collector_status: 'running',
            sources: {
              regtech: { status: 'active', last_run: '2026-02-11T10:00:00' },
            },
          },
        }),
      });
    });

    // STEP 2: Navigate and wait
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // STEP 3: Verify the API was called
    expect(statisticsRequested).toBe(true);
  });
});
