'use client';

import {
  Settings,
  Play,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Lock,
  Clock,
} from 'lucide-react';
import Button from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { COLLECTION_INTERVAL_SECONDS } from '@/types';
import type { Credential, CollectorStatus } from './types';

interface CollectorCardProps {
  credential: Credential;
  collectorStatus?: CollectorStatus;
  testingConnection: boolean;
  triggeringCollection: boolean;
  onTest: (serviceName: string) => void;
  onTrigger: (serviceName: string) => void;
  onEdit: (serviceName: string) => void;
  getSourceCount: (source: string) => number;
  formatInterval: (seconds: number) => string;
}

function getConnectionStatusIcon(status?: string) {
  switch (status) {
    case 'connected':
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case 'error':
    case 'failed':
      return <XCircle className="h-5 w-5 text-red-500" />;
    case 'unknown':
    default:
      return <AlertCircle className="h-5 w-5 text-gray-400" />;
  }
}

function getConnectionStatusBadge(status: string | undefined, configured: boolean) {
  const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
  if (!configured) {
    return (
      <span className={`${baseClasses} bg-gray-100 text-gray-800`}>
        <AlertCircle className="h-3 w-3 mr-1" />
        미설정
      </span>
    );
  }
  switch (status) {
    case 'connected':
      return (
        <span className={`${baseClasses} bg-green-100 text-green-800`}>
          <CheckCircle className="h-3 w-3 mr-1" />
          연결됨
        </span>
      );
    case 'error':
    case 'failed':
      return (
        <span className={`${baseClasses} bg-red-100 text-red-800`}>
          <XCircle className="h-3 w-3 mr-1" />
          오류
        </span>
      );
    case 'unknown':
    default:
      return (
        <span className={`${baseClasses} bg-gray-100 text-gray-800`}>
          <AlertCircle className="h-3 w-3 mr-1" />
          미확인
        </span>
      );
  }
}

export function CollectorCard({
  credential,
  collectorStatus,
  testingConnection,
  triggeringCollection,
  onTest,
  onTrigger,
  onEdit,
  getSourceCount,
  formatInterval,
}: CollectorCardProps) {
  const isEnabled = credential.configured && credential.enabled && collectorStatus?.enabled;
  const canTest = credential.configured && credential.enabled;
  const ipCount = getSourceCount(credential.service_name);

  return (
    <Card padding="lg">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          {getConnectionStatusIcon(credential.connection_status)}
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{credential.service_name}</h3>
            <p className="text-sm text-gray-500">
              {credential.configured ? credential.username : '사용자 미설정'}
            </p>
          </div>
        </div>
        {getConnectionStatusBadge(credential.connection_status, credential.configured)}
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">수집된 IP</p>
          <p className="text-xl font-bold text-gray-900">{ipCount.toLocaleString()}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">수집 간격</p>
          <p className="text-xl font-bold text-gray-900">
            {formatInterval(COLLECTION_INTERVAL_SECONDS[credential.collection_interval])}
          </p>
        </div>
      </div>

      <div className="space-y-2 mb-4 text-sm">
        <div className="flex items-center text-gray-600">
          <Clock className="h-4 w-4 mr-2" />
          <span>
            마지막 수집: {credential.last_collection || collectorStatus?.last_run || '없음'}
          </span>
        </div>
        <div className="flex items-center text-gray-600">
          <Lock className="h-4 w-4 mr-2" />
          <span>상태: {isEnabled ? '활성화' : '비활성화'}</span>
        </div>
        <div className="flex items-center text-gray-600">
          <Settings className="h-4 w-4 mr-2" />
          <span>인증정보: {credential.configured ? '설정됨' : '미설정'}</span>
        </div>
        {credential.status_message && (
          <div className="flex items-center text-gray-600">
            <AlertCircle className="h-4 w-4 mr-2" />
            <span className="truncate">{credential.status_message}</span>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onTest(credential.service_name)}
          loading={testingConnection}
          disabled={!canTest}
          className="min-h-11 whitespace-nowrap"
        >
          <RefreshCw className="h-4 w-4 mr-1" />
          테스트
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onTrigger(credential.service_name)}
          loading={triggeringCollection}
          disabled={!isEnabled}
          className="min-h-11 whitespace-nowrap"
        >
          <Play className="h-4 w-4 mr-1" />
          수집
        </Button>
        <Button
          variant={credential.configured ? 'ghost' : 'primary'}
          size="sm"
          className="min-h-11 whitespace-nowrap"
          onClick={() => onEdit(credential.service_name)}
        >
          <Settings className="h-4 w-4 mr-1" />
          설정 및 저장
        </Button>
      </div>
    </Card>
  );
}
