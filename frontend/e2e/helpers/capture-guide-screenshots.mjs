// Capture dashboard screenshots for the user/admin guides (offline bundle docs).
import { chromium } from 'playwright';
import { mkdtemp, mkdir, rename, rm } from 'node:fs/promises';
import { join } from 'node:path';

const BASE = process.env.BASE_URL || 'https://localhost';
const expectedOrigin = new URL(BASE).origin;
const allowedHosts = new Set(['localhost', '127.0.0.1', '[::1]']);
const OUT = new URL('../../../docs/manual/screenshots/', import.meta.url).pathname;
const username = process.env.E2E_USERNAME;
const password = process.env.E2E_PASSWORD;

if (!username || !password) {
  throw new Error('E2E_USERNAME and E2E_PASSWORD are required');
}
if (!allowedHosts.has(new URL(BASE).hostname)) {
  throw new Error('Guide screenshots may only use a loopback target');
}

const PAGES = [
  ['dashboard', '/'],
  ['ip-management', '/ip-management'],
  ['collection', '/collection'],
  ['analytics', '/analytics'],
  ['fortinet', '/fortinet'],
  ['cloudflare', '/cloudflare'],
  ['database', '/database'],
];

async function sanitizeForDocumentation(page) {
  await page.locator('[data-document-sensitive]').evaluateAll((elements) => {
    for (const element of elements) element.textContent = 'example-user';
  });
  await page.evaluate(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      node.textContent = node.textContent?.replace(
        /\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b/g,
        '192.0.2.10'
      );
    }
  });
  await page.mouse.move(0, 0);
}

await mkdir(OUT, { recursive: true });
const temporary = await mkdtemp(join(OUT, '.capture-'));
const browser = await chromium.launch();

try {
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    viewport: { width: 1440, height: 900 },
    locale: 'ko-KR',
  });
  const page = await context.newPage();

  await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
  if (new URL(page.url()).origin !== expectedOrigin) {
    throw new Error('Login redirected outside the expected origin');
  }
  await page.screenshot({ path: join(temporary, 'login.png') });

  await page
    .locator('input[type="text"], input[name="username"], #username')
    .first()
    .fill(username);
  await page.locator('input[type="password"]').first().fill(password);
  await Promise.all([
    page.waitForURL((url) => url.pathname === '/', { timeout: 15000 }),
    page
      .locator('button[type="submit"], button:has-text("로그인"), button:has-text("Login")')
      .first()
      .click(),
  ]);

  for (const [name, path] of PAGES) {
    await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle' });
    if (new URL(page.url()).origin !== expectedOrigin || page.url().endsWith('/login')) {
      throw new Error(`Protected page did not load: ${path}`);
    }
    await sanitizeForDocumentation(page);
    await page.waitForTimeout(800);
    await page.screenshot({ path: join(temporary, `${name}.png`) });
    console.log('captured', name);
  }

  for (const [name] of [['login'], ...PAGES]) {
    await rename(join(temporary, `${name}.png`), join(OUT, `${name}.png`));
  }
} finally {
  await browser.close();
  await rm(temporary, { recursive: true, force: true });
}
