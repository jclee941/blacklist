/**
 * Playwright E2E Testing Configuration
 *
 * TEST DISCOVERY PATTERN:
 * - testDir: './e2e' (physical directory)
 * - Test files: frontend/e2e/**\/*.spec.ts
 * - File pattern: Files with .spec.ts extension
 *
 * MIGRATION NOTE (2026-02-02):
 * The test structure was migrated from centralized /tests/e2e/ (symlink-based)
 * to frontend/e2e/ (physical directories) to better support CI/CD pipelines
 * and Cloudflare Workers deployment. This was initiated in commit aec04a2.
 *
 * Test files are now co-located with the frontend code they test.
 *
 * STRUCTURE:
 * frontend/e2e/
 * ├── homepage.spec.ts           # Dashboard homepage tests
 * ├── ip-management.spec.ts      # IP management page tests
 * ├── collection.spec.ts         # Data collection tests
 * ├── accessibility.spec.ts      # WCAG accessibility tests
 * ├── performance.spec.ts        # Performance/metrics tests
 * ├── views.spec.ts              # View functionality tests
 * ├── visual-regression.spec.ts  # Visual regression tests
 * └── visual-regression.spec.ts-snapshots/  # Stored snapshots
 *
 * ENVIRONMENT VARIABLES:
 * - WEBKIT_ENABLED=true: Enable webkit/Safari tests (disabled by default, slow)
 * - BASE_URL: Override test target URL (default: http://localhost:2543)
 * - CI: Enable CI-specific settings (retries, single worker)
 *
 * RUNNING E2E TESTS:
 * npm run test:e2e                          # All E2E tests
 * npm run test:e2e -- --project=chromium   # Specific browser
 * npm run test:e2e -- --ui                 # Interactive UI mode
 * npm run test:e2e -- --debug               # Debug mode with inspector
 * WEBKIT_ENABLED=true npm run test:e2e     # Enable Safari tests
 * BASE_URL=http://staging.example.com npm run test:e2e  # Custom URL
 *
 * @see https://playwright.dev/docs/test-configuration
 * @see ./vitest.config.ts (Unit tests)
 * @see ../../.sisyphus/guides/test-commands-quick-reference.md
 */

import { defineConfig, devices } from '@playwright/test';

const webkitEnabled = process.env.WEBKIT_ENABLED === 'true';

export default defineConfig({
  // TEST DISCOVERY: Points to e2e directory
  // Tests are now physically in frontend/e2e/
  testDir: './e2e',

  /* Global test timeout (default 30s is often too short for networkidle) */
  timeout: 60 * 1000,

  /* Assertion timeout */
  expect: {
    timeout: 10 * 1000,
  },

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.BASE_URL || 'http://localhost:2543',

    /* Accept self-signed certificates for staging/sandbox environments */
    ignoreHTTPSErrors: true,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',

    /* Video on failure */
    video: 'retain-on-failure',
  },

  /* Configure projects for major browsers */
  projects: [
    // Smoke tests - fast deployment verification (< 30s)
    // Run with: npm run test:e2e -- --project=smoke
    {
      name: 'smoke',
      testMatch: /smoke\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
      retries: 0,
    },

    {
      name: 'chromium',
      testIgnore: /smoke\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },

    // Firefox disabled - not installed in dev environment
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },

    ...(webkitEnabled
      ? [
          {
            name: 'webkit',
            use: { ...devices['Desktop Safari'] },
          },
        ]
      : []),

    /* Test against branded browsers. */
    // {
    //   name: 'Microsoft Edge',
    //   use: { ...devices['Desktop Edge'], channel: 'msedge' },
    // },
    // {
    //   name: 'Google Chrome',
    //   use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    // },
  ],

  /* Run your local dev server before starting the tests */
  /* Skip webServer when BASE_URL points to external environment */
  webServer:
    process.env.BASE_URL && !process.env.BASE_URL.includes('localhost')
      ? undefined
      : {
          command: 'npm run dev',
          url: 'http://localhost:2543',
          reuseExistingServer: !process.env.CI,
          timeout: 120000,
        },
});
