import { test, expect } from '@playwright/test';
import { loginViaApi } from './auth.fixtures';

test.beforeEach(async ({ page }) => {
  await loginViaApi(page);
});

test.describe('Homepage', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display the page title', async ({ page }) => {
    await expect(page).toHaveTitle(/Blacklist Management Platform|대시보드/);
  });

  test('should render NavBar with logo', async ({ page }) => {
    const logo = page.getByAltText('Nextrade');
    await expect(logo).toBeVisible();
  });
});

test.describe('Homepage - Desktop Only', () => {
  test.skip(({ viewport }) => viewport !== null && viewport.width < 768, 'Desktop only');

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display all navigation menu items', async ({ page }) => {
    const nav = page.locator('nav');
    await expect(nav.getByRole('link', { name: '대시보드' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'IP 관리' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'FortiGate' })).toBeVisible();
    await expect(nav.getByRole('link', { name: '데이터 수집' })).toBeVisible();
    await expect(nav.getByRole('link', { name: '데이터베이스' })).toBeVisible();
  });

  test('should show system status indicator', async ({ page }) => {
    const statusIndicator = page.getByTestId('navbar-status');
    await expect(statusIndicator).toBeVisible();
    await expect(statusIndicator).toContainText('정상');
  });

  test('should navigate to IP Management page', async ({ page }) => {
    await page.getByText('IP 관리').first().click();
    await expect(page).toHaveURL('/ip-management');
  });

  test('should navigate to FortiGate page', async ({ page }) => {
    await page.getByText('FortiGate').first().click();
    await expect(page).toHaveURL('/fortinet');
  });

  test('should navigate to Collection page', async ({ page }) => {
    await page.locator('nav').getByRole('link', { name: '데이터 수집' }).click();
    await expect(page).toHaveURL('/collection');
  });
});

test.describe('Mobile Navigation', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should toggle mobile menu', async ({ page }) => {
    await page.goto('/');

    const menuButton = page.getByTestId('navbar-menu-toggle');
    await expect(menuButton).toBeVisible();

    const mobileMenu = page.getByTestId('navbar-mobile-menu');
    await expect(mobileMenu).not.toBeVisible();

    await menuButton.click();
    await expect(mobileMenu).toBeVisible();

    await menuButton.click();
    await expect(mobileMenu).not.toBeVisible();
  });

  test('should navigate via mobile menu', async ({ page }) => {
    await page.goto('/');

    await page.getByTestId('navbar-menu-toggle').click();

    const mobileMenu = page.getByTestId('navbar-mobile-menu');
    await expect(mobileMenu).toBeVisible();

    await mobileMenu.getByRole('link', { name: 'IP 관리' }).click();

    await expect(page).toHaveURL('/ip-management');
  });
});
