import { test, expect } from '@playwright/test';
import { loginViaApi } from './auth.fixtures';

test.describe('Database Page', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/database');
    await page.waitForLoadState('networkidle');
  });

  test('should display database page header', async ({ page }) => {
    await expect(page.locator('h1').filter({ hasText: '데이터베이스' })).toBeVisible();
  });

  test('should display database content area', async ({ page }) => {
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();
  });

  test('should display database description', async ({ page }) => {
    await expect(page.getByText('PostgreSQL').first()).toBeVisible();
  });
});

test.describe('FortiGate Integration Page', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/fortinet');
    await page.waitForLoadState('networkidle');
  });

  test('should display FortiGate page header', async ({ page }) => {
    await expect(page.locator('h1').filter({ hasText: 'FortiGate' })).toBeVisible();
  });

  test('should display FortiGate content area', async ({ page }) => {
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();
  });
});

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
  });

  test('should display settings page header', async ({ page }) => {
    await expect(page.locator('h1').filter({ hasText: '설정' })).toBeVisible();
  });

  test('should display settings content area', async ({ page }) => {
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();
  });

  test('should display settings tabs', async ({ page }) => {
    await expect(page.getByRole('tab', { name: '시스템 설정' })).toBeVisible();
    await expect(page.getByRole('tab', { name: '보안' })).toBeVisible();
  });
});

test.describe('Monitoring Page Redirect', () => {
  test('should redirect monitoring to dashboard', async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/monitoring');
    await page.waitForLoadState('networkidle');

    const url = page.url();
    expect(url.endsWith('/') || !url.includes('/monitoring')).toBe(true);
  });
});
