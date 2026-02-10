import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: 'standalone',
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
      {
        source: '/metrics',
        destination: `${apiUrl}/metrics`,
      },
      {
        source: '/uiview/:path*',
        destination: `${apiUrl}/:path*`,
      },
      {
        source: '/static/:path*',
        destination: `${apiUrl}/static/:path*`,
      },
    ];
  },
};

export default nextConfig;
