'use client';

import { useState, Suspense } from 'react';
import { Settings, History, Database } from 'lucide-react';
import CollectionManagementClient from './CollectionManagementClient';
import CollectionHistoryClient from './CollectionHistoryClient';
import PageHeader from '@/components/ui/PageHeader';
import Tabs from '@/components/ui/Tabs';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

export default function CollectionPage() {
  const [activeTab, setActiveTab] = useState<string>('management');

  const tabs = [
    { id: 'management', label: '수집 관리', icon: Settings },
    { id: 'history', label: '수집 이력', icon: History },
  ];

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="데이터 수집"
        description="블랙리스트 데이터 수집 관리 및 이력"
        icon={Database}
      />

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      <Suspense fallback={<LoadingSpinner message="데이터 로딩 중..." />}>
        {activeTab === 'management' ? <CollectionManagementClient /> : <CollectionHistoryClient />}
      </Suspense>
    </main>
  );
}
