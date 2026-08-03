// Capture dashboard screenshots for the user/admin guides (offline bundle docs).
import { chromium } from 'playwright';

const BASE = process.env.BASE_URL || 'https://localhost';
const OUT = new URL('../../../docs/manual/screenshots/', import.meta.url).pathname;
const username = process.env.E2E_USERNAME;
const password = process.env.E2E_PASSWORD;

if (!username || !password) {
  throw new Error('E2E_USERNAME and E2E_PASSWORD are required');
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

const browser = await chromium.launch();
const context = await browser.newContext({
  ignoreHTTPSErrors: true,
  viewport: { width: 1440, height: 900 },
  locale: 'ko-KR',
});
const page = await context.newPage();

await page.goto(`${BASE}/login`, { waitUntil: 'networkidle' });
await page.screenshot({ path: `${OUT}/login.png` });

await page.locator('input[type="text"], input[name="username"], #username').first().fill(username);
await page.locator('input[type="password"]').first().fill(password);
await page.locator('button[type="submit"], button:has-text("로그인"), button:has-text("Login")').first().click();
await page.waitForURL('**/', { timeout: 15000 });
await page.waitForLoadState('networkidle');
await page.waitForTimeout(1500);
await page.waitForLoadState('networkidle');

for (const [name, path] of PAGES) {
  await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log('captured', name);
}

await browser.close();
