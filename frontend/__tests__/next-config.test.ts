import { describe, expect, it } from 'vitest';

import nextConfig from '../next.config';

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
});
