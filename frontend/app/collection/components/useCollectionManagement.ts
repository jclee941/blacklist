'use client';

import { useState, useEffect, useCallback } from 'react';
import api, {
  getCredential,
  getCollectionStatus,
  getBlacklistStats,
  testCredential,
  triggerCollectionService,
  updateCredential,
} from '@/lib/api';
import type {
  Credential,
  CollectionStatus,
  BlacklistStats,
  CredentialFormState,
  NotificationState,
  SecudiumCredentialFormState,
} from './types';

const COLLECTORS = ['REGTECH', 'SECUDIUM'];
const REFRESH_INTERVAL = 30000;

const INITIAL_FORM_STATE: CredentialFormState = {
  username: '',
  password: '',
  enabled: true,
  collection_interval: 'daily',
};

const SECUDIUM_INITIAL_FORM_STATE: SecudiumCredentialFormState = {
  username: '',
  password: '',
  enabled: true,
  collection_interval: 'daily',
  otp_mode: 'auto',
  email: '',
  email_password: '',
  imap_server: 'imap.kakao.com',
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
  const [credentialForm, setCredentialForm] = useState<
    CredentialFormState | SecudiumCredentialFormState
  >(INITIAL_FORM_STATE);

  const [showOtpDialog, setShowOtpDialog] = useState(false);
  const [otpServiceName, setOtpServiceName] = useState<string | null>(null);

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
              connection_status: 'unknown' as const,
              otp_mode: data.data.otp_mode,
              email: data.data.email,
              imap_server: data.data.imap_server,
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

      if (data.code === 'otp_required') {
        setOtpServiceName(serviceName);
        setShowOtpDialog(true);
        setNotification({
          type: 'success',
          message: `${serviceName}: OTP 인증이 필요합니다.`,
        });
      } else {
        setCredentials((prev) =>
          prev.map((cred) =>
            cred.service_name === serviceName
              ? {
                  ...cred,
                  connection_status: data.success ? 'connected' : 'failed',
                  status_message: data.message || data.error,
                }
              : cred
          )
        );

        if (data.success) {
          setNotification({ type: 'success', message: `${serviceName} 연결 테스트 성공!` });
        } else {
          setNotification({
            type: 'error',
            message: `${serviceName} 연결 실패: ${data.message || data.error}`,
          });
        }
      }
    } catch {
      setNotification({ type: 'error', message: `${serviceName} 연결 테스트 중 오류 발생` });
    } finally {
      setTestingConnection((prev) => ({ ...prev, [serviceName]: false }));
    }
  }, []);

  const submitOtp = useCallback(
    async (otpCode: string) => {
      if (!otpServiceName) return;

      setTestingConnection((prev) => ({ ...prev, [otpServiceName]: true }));

      try {
        const { data } = await api.post(
          `/proxy/collection/credentials/${otpServiceName.toLowerCase()}/test`,
          {
            otp_code: otpCode,
          }
        );

        setCredentials((prev) =>
          prev.map((cred) =>
            cred.service_name === otpServiceName
              ? {
                  ...cred,
                  connection_status: data.success ? 'connected' : 'failed',
                  status_message: data.message || data.error,
                }
              : cred
          )
        );

        if (data.success) {
          setNotification({ type: 'success', message: `${otpServiceName} OTP 인증 및 연결 성공!` });
          setShowOtpDialog(false);
          setOtpServiceName(null);
        } else {
          setNotification({
            type: 'error',
            message: `${otpServiceName} OTP 인증 실패: ${data.message || data.error}`,
          });
        }
      } catch {
        setNotification({ type: 'error', message: `${otpServiceName} OTP 인증 중 오류 발생` });
      } finally {
        setTestingConnection((prev) => ({ ...prev, [otpServiceName]: false }));
      }
    },
    [otpServiceName]
  );

  const closeOtpDialog = useCallback(() => {
    setShowOtpDialog(false);
    setOtpServiceName(null);
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

      if (serviceName === 'SECUDIUM') {
        setCredentialForm({
          ...SECUDIUM_INITIAL_FORM_STATE,
          username: cred?.username || '',
          enabled: cred?.enabled ?? true,
          collection_interval: cred?.collection_interval || 'daily',
          otp_mode: cred?.otp_mode || 'auto',
          email: cred?.email || '',
          imap_server: cred?.imap_server || 'imap.kakao.com',
        } as SecudiumCredentialFormState);
      } else {
        setCredentialForm({
          ...INITIAL_FORM_STATE,
          username: cred?.username || '',
          enabled: cred?.enabled ?? true,
          collection_interval: cred?.collection_interval || 'daily',
        });
      }

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

    try {
      const data = await updateCredential(
        editingService.toLowerCase(),
        credentialForm as unknown as Record<string, unknown>
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
    }
  }, [editingService, credentialForm, closeEditModal, fetchData]);

  const clearNotification = useCallback(() => {
    setNotification(null);
  }, []);

  const getSourceCount = useCallback(
    (source: string) => {
      if (!blacklistStats?.sources) return 0;
      const found = blacklistStats.sources.find((s) => s.source === source);
      return found?.count || 0;
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
    testingConnection,
    triggeringCollection,
    showCredentialModal,
    editingService,
    notification,
    credentialForm,

    showOtpDialog,
    otpServiceName,

    fetchData,
    testConnection,
    submitOtp,
    closeOtpDialog,
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
