import { test, expect } from '@playwright/test';
import { loginViaApi } from './auth.fixtures';

test.beforeEach(async ({ page }) => {
  await loginViaApi(page);
});

/**
 * Visual Regression Tests
 *
 * These tests capture screenshots and compare them against baseline images
 * to detect unintended visual changes.
 */

test.describe('Visual Regression Tests', () => {
  test.skip(({ browserName }) => browserName === 'webkit', 'No webkit baseline snapshots');

  test('homepage desktop view @visual', async ({ page }) => {
    // Set consistent viewport size for desktop
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Wait for logo to be visible (ensures page is fully loaded)
    await page.getByAltText('Nextrade').waitFor();

    // Mask dynamic content areas that change between runs
    // (real-time logs, collection status, timestamps, counters, table data)
    await page.addStyleTag({
      content: `
        [data-testid="realtime-logs"], [data-testid="collection-status"],
        time, [class*="timestamp"], [class*="log-entry"], [class*="event"],
        [class*="count"], [class*="badge"], [class*="status"],
        table tbody, [class*="chart"], [class*="graph"], [class*="metric"]
        { visibility: hidden !important; }
      `,
    });

    await expect(page).toHaveScreenshot('homepage-desktop.png', {
      timeout: 10000,
      maxDiffPixelRatio: 0.25,
    });
  });

  test('homepage mobile view @visual', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    await page.getByAltText('Nextrade').waitFor();

    // Mask dynamic content that changes between runs
    await page.addStyleTag({
      content: `
        [data-testid="realtime-logs"], [data-testid="collection-status"],
        time, [class*="timestamp"], [class*="log-entry"], [class*="event"],
        [class*="count"], [class*="badge"], [class*="status"],
        table tbody, [class*="chart"], [class*="graph"], [class*="metric"]
        { visibility: hidden !important; }
      `,
    });

    await expect(page).toHaveScreenshot('homepage-mobile.png', {
      timeout: 10000,
      maxDiffPixelRatio: 0.25,
    });
  });

  test('mobile menu open @visual', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Open mobile menu
    await page.getByLabel('메뉴 열기').click();
    await page.getByText('시스템 정상').waitFor();

    // Mask dynamic content that changes between runs
    await page.addStyleTag({
      content: `
        [data-testid="realtime-logs"], [data-testid="collection-status"],
        time, [class*="timestamp"], [class*="log-entry"], [class*="event"],
        [class*="count"], [class*="badge"], [class*="status"],
        table tbody, [class*="chart"], [class*="graph"], [class*="metric"]
        { visibility: hidden !important; }
      `,
    });

    await expect(page).toHaveScreenshot('mobile-menu-open.png', {
      timeout: 10000,
      maxDiffPixelRatio: 0.25,
    });
  });

  test('IP management page @visual', async ({ page }) => {
    await page.goto('/ip-management');
    await page.waitForLoadState('domcontentloaded');

    await expect(page).toHaveScreenshot('ip-management.png', {
      fullPage: true,
      timeout: 10000,
      maxDiffPixelRatio: 0.05,
    });
  });

  test('navigation hover states @visual', async ({ page, viewport }) => {
    test.skip(
      viewport !== null && viewport.width < 768,
      'Desktop only - hover states not applicable on mobile'
    );

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const ipManagementLink = page.getByText('IP 관리').first();
    await ipManagementLink.hover();

    await expect(page).toHaveScreenshot('nav-hover.png', {
      animations: 'disabled',
      timeout: 10000,
      maxDiffPixelRatio: 0.05,
    });
  });
});

test.describe('Component Visual Tests', () => {
  test.skip(({ browserName }) => browserName === 'webkit', 'No webkit baseline snapshots');

  test('navbar component @visual', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const navbar = page.locator('nav');
    await expect(navbar).toHaveScreenshot('navbar-component.png', {
      timeout: 10000,
      maxDiffPixelRatio: 0.05,
    });
  });

  test('system status indicator @visual', async ({ page, viewport }) => {
    test.skip(
      viewport !== null && viewport.width < 768,
      'Desktop only - status indicator hidden on mobile'
    );

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const statusIndicator = page.getByTestId('navbar-status');
    await expect(statusIndicator).toHaveScreenshot('status-indicator.png', {
      timeout: 10000,
      maxDiffPixelRatio: 0.05,
    });
  });
});

test.describe('Responsive Design Tests', () => {
  test.skip(({ browserName }) => browserName === 'webkit', 'No webkit baseline snapshots');

  const viewports = [
    { name: 'mobile-portrait', width: 375, height: 667 },
    { name: 'mobile-landscape', width: 667, height: 375 },
    { name: 'tablet-portrait', width: 768, height: 1024 },
    { name: 'tablet-landscape', width: 1024, height: 768 },
    { name: 'desktop-1920', width: 1920, height: 1080 },
  ];

  for (const viewport of viewports) {
    test(`homepage on ${viewport.name} @visual`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/');
      await page.waitForLoadState('domcontentloaded');

      await page.getByAltText('Nextrade').waitFor();

      await expect(page).toHaveScreenshot(`responsive-${viewport.name}.png`, {
        fullPage: false,
        timeout: 10000,
        maxDiffPixelRatio: 0.25,
      });
    });
  }
});
