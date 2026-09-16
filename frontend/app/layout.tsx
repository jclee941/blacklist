import type { Metadata } from 'next';
import './globals.css';
import NavBar from '@/components/NavBar';
import { AuthGate } from '@/components/AuthGate';

// Rendered per request so Next.js can stamp the per-request CSP nonce onto the inline
// scripts it emits; a prerendered page would ship inline scripts the nonce cannot cover.
export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Blacklist Management Platform',
  description: '실시간 IP 블랙리스트 모니터링 및 관리 플랫폼',
  manifest: '/manifest.json',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-gray-50">
        <AuthGate navigation={<NavBar />}>{children}</AuthGate>
      </body>
    </html>
  );
}
