import type { APIRequestContext, APIResponse, Cookie, Page } from '@playwright/test';

export const AUTH_COOKIE_NAME = 'blacklist_auth';

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

function resolveOrigin(page: Page): string {
  const current = page.url();
  if (current && current !== 'about:blank') {
    return new URL(current).origin;
  }
  return new URL(process.env.BASE_URL ?? 'http://localhost:2543').origin;
}

export async function loginViaApi(page: Page): Promise<string> {
  const token = getSharedAuthToken();
  // The server hands the browser an HttpOnly cookie, so seed the same cookie instead
  // of writing to storage the page can no longer read.
  await page.context().addCookies([
    {
      name: AUTH_COOKIE_NAME,
      value: token,
      url: resolveOrigin(page),
      httpOnly: true,
      sameSite: 'Strict',
    },
  ]);
  return token;
}

export async function getAuthCookie(page: Page): Promise<Cookie | undefined> {
  const cookies = await page.context().cookies();
  return cookies.find((cookie) => cookie.name === AUTH_COOKIE_NAME);
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
