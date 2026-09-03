import type { APIRequestContext, APIResponse, Page } from '@playwright/test';

type E2ECredentials = {
  readonly username: string;
  readonly password: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function parseAuthToken(body: unknown): string {
  const data = isRecord(body) && isRecord(body.data) ? body.data : undefined;
  const token = data?.token ?? (isRecord(body) ? body.token : undefined);
  if (typeof token !== 'string' || token.length === 0) {
    throw new TypeError('Authentication response did not include a token.');
  }
  return token;
}

export function getE2ECredentials(): E2ECredentials {
  const username = process.env.E2E_USERNAME;
  const password = process.env.E2E_PASSWORD;

  if (!username || !password) {
    throw new Error('E2E_USERNAME and E2E_PASSWORD must be set for authenticated E2E tests.');
  }

  return { username, password };
}

export function getSharedAuthToken(): string {
  const token = process.env.E2E_AUTH_TOKEN;
  if (!token) {
    throw new Error('E2E_AUTH_TOKEN must be initialized by the Playwright global setup.');
  }
  return token;
}

export async function loginViaApi(page: Page): Promise<string> {
  const token = getSharedAuthToken();
  await page.addInitScript((value) => {
    const initializationKey = 'blacklist_e2e_auth_initialized';
    if (sessionStorage.getItem(initializationKey) === null) {
      localStorage.setItem('blacklist_auth_token', value);
      sessionStorage.setItem(initializationKey, 'true');
    }
  }, token);
  return token;
}

export async function authenticatedGet(
  request: APIRequestContext,
  path: string
): Promise<APIResponse> {
  const token = getSharedAuthToken();
  return request.get(path, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function authenticatedPost(
  request: APIRequestContext,
  path: string,
  data?: object
): Promise<APIResponse> {
  const token = getSharedAuthToken();
  return request.post(path, {
    headers: { Authorization: `Bearer ${token}` },
    data,
  });
}
