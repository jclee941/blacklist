'use client';

import { Cloud } from 'lucide-react';

import PageHeader from '@/components/ui/PageHeader';
import CloudflareSettings from '@/app/settings/CloudflareSettings';

export default function CloudflarePage() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <PageHeader
        title="Cloudflare 연동"
        description="Cloudflare Lists API 연결 및 블랙리스트 동기화 설정"
        icon={Cloud}
      />

      <section
        aria-label="Cloudflare 연동 설정"
        className="mt-6 rounded-lg bg-white p-6 shadow dark:bg-gray-800"
      >
        <CloudflareSettings />
      </section>
    </main>
  );
}
