import { request } from '@playwright/test';
import { getE2ECredentials, parseAuthToken } from './auth.fixtures';

export default async function globalSetup(): Promise<void> {
  const context = await request.newContext({
    baseURL: process.env.BASE_URL || 'http://localhost:2543',
    ignoreHTTPSErrors: true,
  });
  try {
    const response = await context.post('/api/auth/login', {
      data: getE2ECredentials(),
    });
    if (response.status() !== 200) {
      throw new Error(`E2E global authentication failed with HTTP ${response.status()}.`);
    }
    const body: unknown = await response.json();
    process.env.E2E_AUTH_TOKEN = parseAuthToken(body);
  } finally {
    await context.dispose();
  }
}
