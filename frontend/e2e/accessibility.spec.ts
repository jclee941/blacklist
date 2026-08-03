import { test, expect } from '@playwright/test';
import { loginViaApi } from './auth.fixtures';

test.beforeEach(async ({ page }) => {
  await loginViaApi(page);
});

test.describe('Accessibility Tests', () => {
  test('homepage should have proper semantic HTML', async ({ page }) => {
    await page.goto('/');

    // Check for nav element
    const nav = page.locator('nav');
    await expect(nav).toBeVisible();

    // Check for proper link elements
    const links = page.locator('a');
    const count = await links.count();
    expect(count).toBeGreaterThan(0);
  });

  test('images should have alt text', async ({ page }) => {
    await page.goto('/');

    const logo = page.getByAltText('Nextrade');
    await expect(logo).toBeVisible();
  });

  test('mobile menu button should have aria-label', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    const menuButton = page.getByLabel('메뉴 열기');
    await expect(menuButton).toBeVisible();
  });

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('nav')).toBeVisible();

    // Press Tab to focus first link
    await page.keyboard.press('Tab');

    // Check if a navigation element is focused
    const focused = await page.evaluate(() => {
      const activeElement = document.activeElement;
      return activeElement?.tagName;
    });

    expect(['A', 'BUTTON']).toContain(focused);
  });
});
