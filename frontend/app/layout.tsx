import type { Metadata } from 'next';
import './globals.css';
import NavBar from '@/components/NavBar';
import { AuthGate } from '@/components/AuthGate';

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
