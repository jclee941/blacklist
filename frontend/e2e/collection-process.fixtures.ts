import { type Page } from '@playwright/test';
export { loginViaApi } from './auth.fixtures';

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
            collectors: {
              REGTECH: { enabled: true, running: false, last_run: '2026-02-11T10:00:00' },
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
            ],
          }),
        });
      } else {
        await route.continue();
      }
    }),
    page.route('**/api/collection/credentials/regtech', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              service_name: 'REGTECH',
              configured: true,
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
    page.route('**/api/collection/sources**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [{ name: 'regtech', display_name: 'REGTECH', status: 'active' }],
        }),
      });
    }),
  ]);
}
