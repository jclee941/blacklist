'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  getCredential,
  getCollectionStatus,
  getBlacklistStats,
  testCredential,
  triggerCollectionService,
  updateCredential,
} from '@/lib/api';
import type { CredentialPayload } from '@/types';
import type {
  Credential,
  CollectionStatus,
  BlacklistStats,
  CredentialFormState,
  NotificationState,
} from './types';

const COLLECTORS = ['REGTECH'];
const REFRESH_INTERVAL = 30000;

const INITIAL_FORM_STATE: CredentialFormState = {
  username: '',
  password: '',
  enabled: true,
  collection_interval: 'daily',
};

export function useCollectionManagement() {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [collectionStatus, setCollectionStatus] = useState<CollectionStatus | null>(null);
  const [blacklistStats, setBlacklistStats] = useState<BlacklistStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [testingConnection, setTestingConnection] = useState<Record<string, boolean>>({});
  const [triggeringCollection, setTriggeringCollection] = useState<Record<string, boolean>>({});

  const [showCredentialModal, setShowCredentialModal] = useState(false);
  const [editingService, setEditingService] = useState<string | null>(null);
  const [notification, setNotification] = useState<NotificationState | null>(null);
  const [credentialForm, setCredentialForm] = useState<CredentialFormState>(INITIAL_FORM_STATE);

  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const credPromises = COLLECTORS.map(async (service) => {
        try {
          const data = await getCredential(service.toLowerCase());
          if (data && data.success && data.data) {
            return {
              service_name: data.data.service_name,
              username: data.data.username,
              enabled: data.data.enabled,
              collection_interval: data.data.collection_interval,
              last_collection: data.data.last_collection,
              connection_status: data.data.connection_status ?? ('unknown' as const),
              status_message: data.data.status_message,
            };
          }
        } catch {
          // Credentials not yet configured — return default empty card
        }
        return {
          service_name: service,
          username: '',
          enabled: false,
          collection_interval: 60,
          last_collection: null,
          connection_status: 'unknown' as const,
        };
      });

      const credResults = await Promise.all(credPromises);
      const validCreds = credResults.filter((c) => c !== null) as Credential[];
      setCredentials(validCreds);

      const statusData = await getCollectionStatus();
      if (statusData && statusData.success && statusData.data) {
        setCollectionStatus(statusData.data);
      }

      const statsData = await getBlacklistStats();
      if (statsData && statsData.success && statsData.data) {
        setBlacklistStats(statsData.data);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  const testConnection = useCallback(async (serviceName: string) => {
    setTestingConnection((prev) => ({ ...prev, [serviceName]: true }));
    try {
      const data = await testCredential(serviceName.toLowerCase());
      const innerData = data?.data;

      const isConnected = innerData?.status === 'connected';
      setCredentials((prev) =>
        prev.map((cred) =>
          cred.service_name === serviceName
            ? {
                ...cred,
                connection_status: isConnected ? 'connected' : 'failed',
                status_message: innerData?.message || innerData?.error_code,
              }
            : cred
        )
      );

      if (isConnected) {
        setNotification({ type: 'success', message: `${serviceName} 연결 테스트 성공!` });
      } else {
        setNotification({
          type: 'error',
          message: `${serviceName} 연결 실패: ${innerData?.message || innerData?.error_code || '알 수 없는 오류'}`,
        });
      }
    } catch {
      setNotification({ type: 'error', message: `${serviceName} 연결 테스트 중 오류 발생` });
    } finally {
      setTestingConnection((prev) => ({ ...prev, [serviceName]: false }));
    }
  }, []);

  const triggerCollection = useCallback(
    async (serviceName: string) => {
      setTriggeringCollection((prev) => ({ ...prev, [serviceName]: true }));
      try {
        const data = await triggerCollectionService(serviceName.toLowerCase(), { force: true });

        if (data.success) {
          setNotification({
            type: 'success',
            message: `${serviceName} 수집 작업이 시작되었습니다!`,
          });
          setTimeout(fetchData, 2000);
        } else {
          setNotification({
            type: 'error',
            message: `${serviceName} 수집 실패: ${data.error || '알 수 없는 오류'}`,
          });
        }
      } catch {
        setNotification({ type: 'error', message: `${serviceName} 수집 작업 중 오류 발생` });
      } finally {
        setTriggeringCollection((prev) => ({ ...prev, [serviceName]: false }));
      }
    },
    [fetchData]
  );

  const openEditModal = useCallback(
    (serviceName: string) => {
      const cred = credentials.find((c) => c.service_name === serviceName);
      setEditingService(serviceName);

      setCredentialForm({
        ...INITIAL_FORM_STATE,
        username: cred?.username || '',
        enabled: cred?.enabled ?? true,
        collection_interval: cred?.collection_interval || 'daily',
      });

      setShowCredentialModal(true);
    },
    [credentials]
  );

  const closeEditModal = useCallback(() => {
    setShowCredentialModal(false);
    setEditingService(null);
    setCredentialForm(INITIAL_FORM_STATE);
  }, []);

  const saveCredentials = useCallback(async () => {
    if (!editingService) return;

    if (!credentialForm.username.trim()) {
      setNotification({ type: 'error', message: '사용자명을 입력하세요.' });
      return;
    }

    const existingCred = credentials.find((c) => c.service_name === editingService);
    if (!existingCred?.username && !credentialForm.password.trim()) {
      setNotification({ type: 'error', message: '비밀번호를 입력하세요.' });
      return;
    }

    setSaving(true);
    try {
      const data = await updateCredential(
        editingService.toLowerCase(),
        credentialForm as unknown as CredentialPayload
      );

      if (data.success) {
        setNotification({
          type: 'success',
          message: `${editingService} 인증 정보가 저장되었습니다!`,
        });
        closeEditModal();
        fetchData();
      } else {
        setNotification({
          type: 'error',
          message: `저장 실패: ${data.error || '알 수 없는 오류'}`,
        });
      }
    } catch {
      setNotification({ type: 'error', message: '저장 중 오류 발생' });
    } finally {
      setSaving(false);
    }
  }, [editingService, credentialForm, credentials, closeEditModal, fetchData]);

  const clearNotification = useCallback(() => {
    setNotification(null);
  }, []);

  const getSourceCount = useCallback(
    (source: string) => {
      if (!blacklistStats?.sources) return 0;
      const entry = blacklistStats.sources[source];
      return entry?.total_items ?? entry?.count ?? entry?.cumulative_collected ?? 0;
    },
    [blacklistStats]
  );

  const formatInterval = useCallback((seconds: number) => {
    if (seconds >= 86400) return `${Math.floor(seconds / 86400)}일`;
    if (seconds >= 3600) return `${Math.floor(seconds / 3600)}시간`;
    return `${Math.floor(seconds / 60)}분`;
  }, []);

  return {
    credentials,
    collectionStatus,
    blacklistStats,
    loading,
    saving,
    testingConnection,
    triggeringCollection,
    showCredentialModal,
    editingService,
    notification,
    credentialForm,

    fetchData,
    testConnection,
    triggerCollection,
    openEditModal,
    closeEditModal,
    saveCredentials,
    clearNotification,
    setCredentialForm,

    getSourceCount,
    formatInterval,
  };
}
