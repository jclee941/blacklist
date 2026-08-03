import { expect, type APIRequestContext, type APIResponse, type Page } from '@playwright/test';

type E2ECredentials = {
  readonly username: string;
  readonly password: string;
};

export function getE2ECredentials(): E2ECredentials {
  const username = process.env.E2E_USERNAME;
  const password = process.env.E2E_PASSWORD;

  if (!username || !password) {
    throw new Error('E2E_USERNAME and E2E_PASSWORD must be set for authenticated E2E tests.');
  }

  return { username, password };
}

async function getAuthToken(request: APIRequestContext): Promise<string> {
  const response = await request.post('/api/auth/login', {
    data: getE2ECredentials(),
  });
  expect(response.status()).toBe(200);

  const body = await response.json();
  const token = body.data?.token ?? body.token;
  if (typeof token !== 'string' || token.length === 0) {
    throw new TypeError('Authentication response did not include a token.');
  }
  return token;
}

export async function loginViaApi(page: Page): Promise<void> {
  const token = await getAuthToken(page.request);
  await page.addInitScript((value) => {
    localStorage.setItem('blacklist_auth_token', value);
  }, token);
}

export async function authenticatedGet(
  request: APIRequestContext,
  path: string
): Promise<APIResponse> {
  const token = await getAuthToken(request);
  return request.get(path, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function authenticatedPost(
  request: APIRequestContext,
  path: string,
  data?: object
): Promise<APIResponse> {
  const token = await getAuthToken(request);
  return request.post(path, {
    headers: { Authorization: `Bearer ${token}` },
    data,
  });
}
