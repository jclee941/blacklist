import { expect, test } from '@playwright/test';

test('Cloudflare 연동 탭에서 기존 설정 화면을 연다', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('link', { name: 'Cloudflare 연동' }).click();

  await expect(page).toHaveURL(/\/cloudflare$/);
  await expect(page.getByRole('heading', { name: 'Cloudflare 연동' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Cloudflare WAF 연동' })).toBeVisible();
  await expect(page.getByLabel('API Token')).toBeVisible();
});
