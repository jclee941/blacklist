import { type Page } from '@playwright/test';

export async function loginViaApi(page: Page) {
  const res = await page.request.post('/api/auth/login', {
    data: { username: 'admin', password: 'admin' },
  });
  const body = await res.json();
  const token = body.data?.token || body.token;
  if (token) {
    await page.goto('/');
    await page.evaluate((t) => localStorage.setItem('blacklist_auth_token', t), token);
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
  }
}

export function mockCollectionApis(page: Page) {
  return Promise.all([
    page.route('**/api/collection/status**', async (route) => {
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
    }),
    page.route('**/api/collection/statistics**', async (route) => {
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
    }),
    page.route('**/api/collection/credentials', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: [
              {
                service_name: 'REGTECH',
                username: 'regtech_user',
                connection_status: 'connected',
                status_message: '연결됨',
                last_test: '2026-02-11T10:00:00',
              },
              {
                service_name: 'SECUDIUM',
                username: 'secudium_user',
                connection_status: 'connected',
                status_message: '연결됨',
                last_test: '2026-02-11T09:30:00',
              },
            ],
          }),
        });
      } else {
        await route.continue();
      }
    }),
    page.route('**/proxy/collection/credentials/regtech', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              service_name: 'REGTECH',
              username: 'regtech_user',
              enabled: true,
              collection_interval: 'daily',
              connection_status: 'connected',
              status_message: '연결됨',
            },
          }),
        });
      } else {
        await route.continue();
      }
    }),
    page.route('**/proxy/collection/credentials/secudium', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              service_name: 'SECUDIUM',
              username: 'secudium_user',
              enabled: true,
              collection_interval: 'daily',
              connection_status: 'connected',
              status_message: '연결됨',
            },
          }),
        });
      } else {
        await route.continue();
      }
    }),
    page.route('**/api/collection/sources**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            { name: 'regtech', display_name: 'REGTECH', status: 'active' },
            { name: 'secudium', display_name: 'SECUDIUM', status: 'active' },
          ],
        }),
      });
    }),
  ]);
}
