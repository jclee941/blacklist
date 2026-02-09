import { useState, useEffect, useCallback } from 'react';
import {
  getCredential,
  getCollectionStatus,
  getBlacklistStats,
  testCredential,
  triggerCollectionService,
} from '@/lib/api';
import type { Credential, CollectionStatus, BlacklistStats, COLLECTORS } from '../types';

interface UseCollectionDataReturn {
  credentials: Credential[];
  collectionStatus: CollectionStatus | null;
  blacklistStats: BlacklistStats | null;
  loading: boolean;
  testingConnection: Record<string, boolean>;
  triggeringCollection: Record<string, boolean>;
  fetchData: () => Promise<void>;
  handleTestConnection: (serviceName: string) => Promise<void>;
  handleTriggerCollection: (serviceName: string) => Promise<void>;
}

const COLLECTOR_LIST = ['REGTECH', 'SECUDIUM'] as const;

export function useCollectionData(): UseCollectionDataReturn {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [collectionStatus, setCollectionStatus] = useState<CollectionStatus | null>(null);
  const [blacklistStats, setBlacklistStats] = useState<BlacklistStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [testingConnection, setTestingConnection] = useState<Record<string, boolean>>({});
  const [triggeringCollection, setTriggeringCollection] = useState<Record<string, boolean>>({});

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const credPromises = COLLECTOR_LIST.map(async (service) => {
        try {
          const data = await getCredential(service.toLowerCase());
          if (data?.success && data.data) {
            return {
              service_name: data.data.service_name,
              username: data.data.username,
              enabled: data.data.enabled,
              collection_interval: data.data.collection_interval,
              last_collection: data.data.last_collection,
              connection_status: 'unknown' as const,
            };
          }
        } catch (error) {
          console.error(`Failed to fetch ${service} credentials:`, error);
        }
        return null;
      });

      const credResults = await Promise.all(credPromises);
      setCredentials(credResults.filter((c) => c !== null) as Credential[]);

      const statusData = await getCollectionStatus();
      if (statusData?.success) {
        setCollectionStatus(statusData.data);
      }

      const statsData = await getBlacklistStats();
      if (statsData?.success) {
        setBlacklistStats(statsData.data);
      }
    } catch (error) {
      console.error('Failed to fetch collection data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleTestConnection = useCallback(async (serviceName: string) => {
    setTestingConnection((prev) => ({ ...prev, [serviceName]: true }));
    try {
      await testCredential(serviceName.toLowerCase());
    } catch (error) {
      console.error('Connection test failed:', error);
    } finally {
      setTestingConnection((prev) => ({ ...prev, [serviceName]: false }));
    }
  }, []);

  const handleTriggerCollection = useCallback(
    async (serviceName: string) => {
      setTriggeringCollection((prev) => ({ ...prev, [serviceName]: true }));
      try {
        await triggerCollectionService(serviceName.toLowerCase());
        await fetchData();
      } catch (error) {
        console.error('Collection trigger failed:', error);
      } finally {
        setTriggeringCollection((prev) => ({ ...prev, [serviceName]: false }));
      }
    },
    [fetchData]
  );

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return {
    credentials,
    collectionStatus,
    blacklistStats,
    loading,
    testingConnection,
    triggeringCollection,
    fetchData,
    handleTestConnection,
    handleTriggerCollection,
  };
}
