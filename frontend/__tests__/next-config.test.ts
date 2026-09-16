import { describe, expect, it, vi } from 'vitest';

import nextConfig from '../next.config';

const headerKeysOf = async (config: typeof nextConfig): Promise<string[]> => {
  const rules = await config.headers?.();
  return rules?.[0]?.headers.map(({ key }) => key) ?? [];
};

describe('Next security boundary', () => {
  it('exposes only the supported backend rewrites', async () => {
    const rewrites = await nextConfig.rewrites?.();

    expect(rewrites).toEqual([
      { source: '/api/:path*', destination: 'http://localhost:2542/api/:path*' },
      { source: '/health', destination: 'http://localhost:2542/health' },
    ]);
  });

  it('applies browser security headers to every route', async () => {
    const rules = await nextConfig.headers?.();
    const headers = Object.fromEntries(
      rules?.[0]?.headers.map(({ key, value }) => [key, value]) ?? []
    );

    expect(rules?.[0]?.source).toBe('/:path*');
    expect(headers).toMatchObject({
      'Content-Security-Policy': expect.stringContaining("frame-ancestors 'none'"),
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
    });
  });

  it('leaves the production CSP to the custom server so its per-request nonce survives', async () => {
    // server.js mints a nonce and sends its own policy. A policy emitted here would
    // replace that header with a nonce-less value and the browser would block Next's
    // inline scripts.
    vi.resetModules();
    vi.stubEnv('NODE_ENV', 'production');
    try {
      const productionConfig = (await import('../next.config')).default;
      const keys = await headerKeysOf(productionConfig);

      expect(keys).not.toContain('Content-Security-Policy');
      expect(keys).toContain('X-Frame-Options');
    } finally {
      vi.unstubAllEnvs();
      vi.resetModules();
    }
  });
});
