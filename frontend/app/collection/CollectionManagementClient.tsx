'use client';

import { RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';
import Button from '@/components/ui/Button';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import PageHeader from '@/components/ui/PageHeader';
import {
  CollectionStats,
  CollectorCard,
  CredentialEditModal,
  OtpInputDialog,
  useCollectionManagement,
  type Credential,
  type CollectorStatus,
} from './components';

const COLLECTORS = ['REGTECH', 'SECUDIUM'];

export default function CollectionManagementClient() {
  const {
    credentials,
    collectionStatus,
    blacklistStats,
    loading,
    testingConnection,
    triggeringCollection,
    showCredentialModal,
    editingService,
    notification,
    credentialForm,
    fetchData,
    saveCredentials,
    testConnection,
    triggerCollection,
    openEditModal,
    closeEditModal,
    setCredentialForm,
    getSourceCount,
    formatInterval,
    showOtpDialog,
    otpServiceName,
    submitOtp,
    closeOtpDialog,
  } = useCollectionManagement();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" message="수집 정보를 불러오는 중..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="수집 관리" description="외부 데이터 소스에서 블랙리스트 IP를 수집합니다" />

      {notification && (
        <div
          className={`p-4 rounded-lg flex items-center space-x-2 ${
            notification.type === 'success'
              ? 'bg-green-500/10 text-green-400 border border-green-500/20'
              : notification.type === 'error'
                ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
          }`}
        >
          {notification.type === 'success' ? (
            <CheckCircle className="h-5 w-5" />
          ) : notification.type === 'error' ? (
            <AlertCircle className="h-5 w-5" />
          ) : (
            <AlertCircle className="h-5 w-5" />
          )}
          <span>{notification.message}</span>
        </div>
      )}

      <CollectionStats
        collectionStatus={collectionStatus}
        blacklistStats={blacklistStats}
        loading={loading}
      />

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-100">수집기</h2>
        <Button variant="ghost" size="sm" onClick={fetchData}>
          <RefreshCw className="h-4 w-4 mr-1" />
          새로고침
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {COLLECTORS.map((name) => {
          const credential = credentials.find(
            (c: Credential) => c.service_name.toUpperCase() === name
          );
          const collectorStatus = collectionStatus?.collectors?.[name.toLowerCase()] as
            | CollectorStatus
            | undefined;

          if (!credential) return null;

          return (
            <CollectorCard
              key={name}
              credential={credential}
              collectorStatus={collectorStatus}
              testingConnection={testingConnection[credential.service_name] || false}
              triggeringCollection={triggeringCollection[credential.service_name] || false}
              onTest={testConnection}
              onTrigger={triggerCollection}
              onEdit={openEditModal}
              getSourceCount={getSourceCount}
              formatInterval={formatInterval}
            />
          );
        })}
      </div>

      <CredentialEditModal
        show={showCredentialModal}
        onClose={closeEditModal}
        editingService={editingService}
        credentialForm={credentialForm}
        onFormChange={setCredentialForm}
        onSave={saveCredentials}
        loading={loading}
      />

      <OtpInputDialog
        show={showOtpDialog}
        onClose={closeOtpDialog}
        onSubmit={submitOtp}
        loading={otpServiceName ? testingConnection[otpServiceName] : false}
        serviceName={otpServiceName || ''}
      />
    </div>
  );
}
