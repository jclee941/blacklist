'use client';

import { Activity, Database, Clock, TrendingUp } from 'lucide-react';
import { StatCard } from '@/components/ui/Card';
import type { CollectionStatus, BlacklistStats } from './types';

interface CollectionStatsProps {
  collectionStatus: CollectionStatus | null;
  blacklistStats: BlacklistStats | null;
  loading: boolean;
}

export function CollectionStats({
  collectionStatus,
  blacklistStats,
  loading,
}: CollectionStatsProps) {
  const activeCollectors = collectionStatus
    ? Object.values(collectionStatus.collectors).filter((c) => c.enabled).length
    : 0;
  const totalCollectors = collectionStatus ? Object.keys(collectionStatus.collectors).length : 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <StatCard
        title="수집 상태"
        value={collectionStatus?.is_running ? '수집 중' : '대기 중'}
        icon={Activity}
        trend={collectionStatus?.is_running ? { value: 0, isPositive: true } : undefined}
        loading={loading}
      />
      <StatCard
        title="현재 등록 IP"
        value={blacklistStats?.current_total_ips?.toLocaleString() ?? '0'}
        icon={Database}
        loading={loading}
      />
      <StatCard
        title="활성 수집기"
        value={`${activeCollectors}/${totalCollectors}`}
        icon={TrendingUp}
        loading={loading}
      />
      <StatCard
        title="마지막 업데이트"
        value={
          collectionStatus?.collectors
            ? (() => {
                const lastRuns = Object.values(collectionStatus.collectors)
                  .map((c) => c.last_run)
                  .filter(Boolean) as string[];
                if (lastRuns.length === 0) return '-';
                const latest = lastRuns.sort().reverse()[0];
                return new Date(latest).toLocaleString('ko-KR');
              })()
            : '-'
        }
        icon={Clock}
        loading={loading}
      />
    </div>
  );
}
