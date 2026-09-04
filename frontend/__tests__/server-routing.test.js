import routing from '../server-routing.js';
import { vi } from 'vitest';

const {
  createProxyHeaders,
  isProxyBodyTooLarge,
  parseNextUrl,
  resolveProxyTarget,
  resolveStaticTarget,
  sendProxyJsonError,
} = routing;

describe('custom server routing', () => {
  it('proxies only supported backend endpoints', () => {
    expect(resolveProxyTarget('/api/auth/me?fresh=true')).toBe('/api/auth/me?fresh=true');
    expect(resolveProxyTarget('/health?verbose=true')).toBe('/health');
  });

  it('parses paths and repeated query values for the Next handler', () => {
    expect(parseNextUrl('/collection?page=2&source=REGTECH&source=MANUAL')).toEqual({
      pathname: '/collection',
      query: { page: '2', source: ['REGTECH', 'MANUAL'] },
    });
  });

  it('rejects malformed request targets without throwing', () => {
    expect(parseNextUrl('//%')).toBeNull();
  });

  it.each([
    '/uiview/../../ssl/server.key',
    '/static/../../server.js',
    '/metrics',
    '/_next/static/../../server.js',
    '/../ssl/server.key',
  ])('leaves filesystem and legacy paths to Next: %s', (pathname) => {
    expect(resolveProxyTarget(pathname)).toBeNull();
  });

  it('maps static and public files only inside their roots', () => {
    expect(resolveStaticTarget('/app', '/_next/static/chunks/app.js')).toEqual({
      base: '/app/.next/static',
      cacheControl: 'public, max-age=31536000, immutable',
      candidate: '/app/.next/static/chunks/app.js',
    });
    expect(resolveStaticTarget('/app', '/logo.svg')).toEqual({
      base: '/app/public',
      cacheControl: 'public, max-age=86400',
      candidate: '/app/public/logo.svg',
    });
  });

  it.each([
    '/_next/static/../../server.js',
    '/_next/static/%2e%2e/server.js',
    '/../ssl/server.key',
    '/%2e%2e/ssl/server.key',
    '/api/../server.js',
  ])('rejects static path escape: %s', (pathname) => {
    expect(resolveStaticTarget('/app', pathname)).toBeNull();
  });

  it('replaces untrusted forwarding headers with the socket peer', () => {
    const headers = createProxyHeaders(
      {
        authorization: 'Bearer token',
        connection: 'keep-alive',
        forwarded: 'for=198.51.100.12',
        host: 'attacker.invalid',
        'proxy-authorization': 'Basic value',
        'x-forwarded-for': '203.0.113.10',
        'x-forwarded-host': 'attacker.invalid',
        'x-forwarded-port': '80',
        'x-forwarded-prefix': '/admin',
        'x-forwarded-proto': 'http',
        'x-real-ip': '203.0.113.11',
      },
      '172.20.0.5',
      'blacklist-app:2542',
      'https',
    );

    expect(headers).toMatchObject({
      authorization: 'Bearer token',
      host: 'blacklist-app:2542',
      'x-forwarded-for': '172.20.0.5',
      'x-forwarded-proto': 'https',
      'x-real-ip': '172.20.0.5',
    });
    expect(headers).not.toHaveProperty('connection');
    expect(headers).not.toHaveProperty('forwarded');
    expect(headers).not.toHaveProperty('x-forwarded-host');
    expect(headers).not.toHaveProperty('x-forwarded-port');
    expect(headers).not.toHaveProperty('x-forwarded-prefix');
    expect(headers).not.toHaveProperty('proxy-authorization');
  });

  it('rejects invalid or oversized declared request bodies', () => {
    expect(isProxyBodyTooLarge({}, 1024)).toBe(false);
    expect(isProxyBodyTooLarge({ 'content-length': '1024' }, 1024)).toBe(false);
    expect(isProxyBodyTooLarge({ 'content-length': '1025' }, 1024)).toBe(true);
    expect(isProxyBodyTooLarge({ 'content-length': 'invalid' }, 1024)).toBe(true);
  });

  it('does not write a second response after upstream headers started', () => {
    const response = {
      headersSent: true,
      writableEnded: false,
      destroyed: false,
      destroy: vi.fn(),
      writeHead: vi.fn(),
      end: vi.fn(),
    };

    expect(sendProxyJsonError(response, 413, 'REQUEST_TOO_LARGE')).toBe(false);
    expect(response.destroy).toHaveBeenCalledOnce();
    expect(response.writeHead).not.toHaveBeenCalled();
    expect(response.end).not.toHaveBeenCalled();
  });
});
