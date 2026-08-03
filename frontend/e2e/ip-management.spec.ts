import { test, expect } from '@playwright/test';
import { loginViaApi } from './auth.fixtures';

test.beforeEach(async ({ page }) => {
  await loginViaApi(page);
});

test.describe('IP Management Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ip-management');
  });

  test('should display IP Management page', async ({ page }) => {
    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Check if NavBar is visible
    const logo = page.getByAltText('Nextrade');
    await expect(logo).toBeVisible();
  });

  test('should have working navigation back to dashboard', async ({ page, isMobile }) => {
    if (isMobile) {
      await page.getByTestId('navbar-menu-toggle').click();
      await page.getByTestId('navbar-mobile-menu').getByRole('link', { name: '대시보드' }).click();
    } else {
      await page.locator('nav').getByRole('link', { name: '대시보드' }).click();
    }
    await expect(page).toHaveURL('/');
  });
});

test.describe('Database Page', () => {
  test('should display database page', async ({ page }) => {
    await page.goto('/database');
    await page.waitForLoadState('networkidle');

    const logo = page.getByAltText('Nextrade');
    await expect(logo).toBeVisible();
  });
});

test.describe('Collection Page', () => {
  test('should display collection page', async ({ page }) => {
    await page.goto('/collection');
    await page.waitForLoadState('networkidle');

    const logo = page.getByAltText('Nextrade');
    await expect(logo).toBeVisible();
  });
});

test.describe('Monitoring Page', () => {
  test('should display monitoring page', async ({ page }) => {
    await page.goto('/monitoring');
    await page.waitForLoadState('networkidle');

    const logo = page.getByAltText('Nextrade');
    await expect(logo).toBeVisible();
  });
});

test.describe('FortiGate Page', () => {
  test('should display fortinet page', async ({ page }) => {
    await page.goto('/fortinet');
    await page.waitForLoadState('networkidle');

    const logo = page.getByAltText('Nextrade');
    await expect(logo).toBeVisible();
  });
});
