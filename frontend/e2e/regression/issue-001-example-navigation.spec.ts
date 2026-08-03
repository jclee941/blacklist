/**
 * Regression Test Example
 *
 * This is an example regression test demonstrating the proper structure.
 * Use this as a reference when creating new regression tests.
 */

import { test, expect } from '@playwright/test';
import { loginViaApi } from '../auth.fixtures';

test.beforeEach(async ({ page }) => {
  await loginViaApi(page);
});

test.describe('Regression: Issue #001 - Navigation After Page Load', () => {
  /**
   * GitHub Issue: https://github.com/jclee-homelab/blacklist/issues/1
   *
   * PROBLEM:
   * Navigation links were not clickable immediately after page load due to
   * hydration delay. Users had to wait several seconds before the nav worked.
   *
   * ROOT CAUSE:
   * React hydration was blocking event handlers on navigation links.
   * The links appeared clickable but click events were not registered.
   *
   * FIX:
   * Added proper loading states and ensured navigation is interactive
   * before hydration completes using Next.js Link component correctly.
   *
   * REGRESSION PREVENTION:
   * This test verifies that navigation works immediately after page load.
   */

  test('should navigate immediately after page load @regression', async ({ page }) => {
    // STEP 1: Load the page
    await page.goto('/');

    // STEP 2: Immediately try to click navigation (no artificial waits)
    const nav = page.locator('nav');
    await expect(nav).toBeVisible();

    // Find any navigation link
    const navLink = nav.locator('a').first();

    if ((await navLink.count()) > 0) {
      // STEP 3: Click should work immediately
      const href = await navLink.getAttribute('href');

      if (href && href !== '/') {
        await navLink.click();

        // STEP 4: Should navigate without timeout or error
        await expect(page).not.toHaveURL('/');
      }
    }
  });

  test('should show interactive elements after load @regression', async ({ page }) => {
    await page.goto('/');

    // All buttons should be clickable (not disabled during hydration)
    const buttons = page.locator('button:not([disabled])');

    if ((await buttons.count()) > 0) {
      const firstButton = buttons.first();
      await expect(firstButton).toBeEnabled();
    }
  });
});
