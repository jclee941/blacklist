const path = require('path');

const HOP_BY_HOP_HEADERS = new Set([
  'connection',
  'forwarded',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
  'x-forwarded-for',
  'x-real-ip',
]);

const SECURITY_HEADERS = {
  'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
  'Permissions-Policy': 'camera=(), geolocation=(), microphone=()',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
};

const createProxyHeaders = (incomingHeaders, clientIp, targetHost) => {
  const headers = {};
  for (const [name, value] of Object.entries(incomingHeaders)) {
    if (!HOP_BY_HOP_HEADERS.has(name.toLowerCase()) && name.toLowerCase() !== 'host') {
      headers[name] = value;
    }
  }

  return {
    ...headers,
    host: targetHost,
    'x-forwarded-for': clientIp,
    'x-real-ip': clientIp,
  };
};

const resolveProxyTarget = (requestUrl) => {
  const parsed = new URL(requestUrl, 'http://frontend.invalid');
  if (parsed.pathname.startsWith('/api/')) {
    return `${parsed.pathname}${parsed.search}`;
  }
  if (parsed.pathname === '/health') {
    return parsed.pathname;
  }
  return null;
};

const parseNextUrl = (requestUrl) => {
  try {
    const parsed = new URL(requestUrl, 'https://frontend.invalid');
    const query = {};
    for (const [name, value] of parsed.searchParams) {
      const current = query[name];
      if (current === undefined) {
        query[name] = value;
      } else if (Array.isArray(current)) {
        current.push(value);
      } else {
        query[name] = [current, value];
      }
    }
    return { pathname: parsed.pathname, query };
  } catch {
    return null;
  }
};

const resolveStaticTarget = (applicationRoot, requestUrl) => {
  let decodedPath;
  try {
    decodedPath = decodeURIComponent(requestUrl.split('?', 1)[0]);
  } catch {
    return null;
  }
  if (decodedPath.includes('\0') || decodedPath.split(/[\\/]/).includes('..')) {
    return null;
  }

  const { pathname } = new URL(requestUrl, 'https://frontend.invalid');
  let base;
  let cacheControl;
  let relativePath;
  if (pathname.startsWith('/_next/static/')) {
    base = path.resolve(applicationRoot, '.next', 'static');
    cacheControl = 'public, max-age=31536000, immutable';
    relativePath = pathname.slice('/_next/static/'.length);
  } else if (
    pathname.startsWith('/') &&
    !pathname.startsWith('/_next/') &&
    !pathname.startsWith('/api/') &&
    pathname !== '/health'
  ) {
    base = path.resolve(applicationRoot, 'public');
    cacheControl = 'public, max-age=86400';
    relativePath = pathname.slice(1);
  } else {
    return null;
  }

  const candidate = path.resolve(base, relativePath);
  if (candidate === base || !candidate.startsWith(`${base}${path.sep}`)) {
    return null;
  }
  return { base, cacheControl, candidate };
};

const setSecurityHeaders = (response) => {
  for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
    response.setHeader(name, value);
  }
};

module.exports = {
  SECURITY_HEADERS,
  createProxyHeaders,
  parseNextUrl,
  resolveProxyTarget,
  resolveStaticTarget,
  setSecurityHeaders,
};
