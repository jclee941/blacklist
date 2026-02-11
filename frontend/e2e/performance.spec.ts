import { test, expect } from '@playwright/test';

test.describe('Performance Tests', () => {
  test('homepage should load within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    // Should load within 30 seconds (includes cold start in dev/CI)
    expect(loadTime).toBeLessThan(30000);
  });

  test('should not have console errors on homepage', async ({ page }) => {
    const errors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Filter out known acceptable errors (like 404 for optional resources)
    const criticalErrors = errors.filter(
      (error) => !error.includes('404') && !error.includes('favicon')
    );

    expect(criticalErrors.length).toBe(0);
  });

  test('images should load properly', async ({ page }) => {
    await page.goto('/');

    const logo = page.getByAltText('Nextrade');
    await expect(logo).toBeVisible();

    // Check if image is actually loaded
    const isLoaded = await logo.evaluate((img: HTMLImageElement) => {
      return img.complete && img.naturalHeight !== 0;
    });

    expect(isLoaded).toBeTruthy();
  });
});
