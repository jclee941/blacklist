import type { NextConfig } from 'next';

// Production responses get their Content-Security-Policy from server.js /
// server-routing.js, which mints a per-request nonce for script-src. A second policy
// emitted here would override that header with a nonce-less value and the browser
// would block Next's inline scripts, so this one is scoped to `next dev`, whose HMR
// runtime needs 'unsafe-inline'.
const isDevelopment = process.env.NODE_ENV !== 'production';

const developmentContentSecurityPolicy =
  "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  output: 'standalone',
  outputFileTracingRoot: __dirname,
  turbopack: {
    root: __dirname,
  },
  async redirects() {
    return [
      {
        source: '/monitoring',
        destination: '/',
        permanent: false,
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          ...(isDevelopment
            ? [{ key: 'Content-Security-Policy', value: developmentContentSecurityPolicy }]
            : []),
          { key: 'Permissions-Policy', value: 'camera=(), geolocation=(), microphone=()' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
        ],
      },
    ];
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:2542';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
      {
        source: '/health',
        destination: `${apiUrl}/health`,
      },
    ];
  },
};

export default nextConfig;
