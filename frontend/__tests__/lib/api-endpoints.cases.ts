import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getMocks } from './api-test-helpers';
import {
  addIP,
  deleteIP,
  exportBlacklistRaw,
  getBlacklist,
  getBlacklistStats,
  getCloudflareCredentials,
  getCollectionHistory,
  getCollectionStatistics,
  getCollectionStatus,
  getCredential,
  getDailyDetectionStats,
  getDatabaseSchema,
  getDatabaseTables,
  getFortinetBlocklist,
  getFortinetPullLogs,
  getSettingsGrouped,
  getStats,
  getSystemStatus,
  getUnifiedIPs,
  getWhitelist,
  saveCloudflareCredentials,
  searchIP,
  testCloudflareConnection,
  testCredential,
  triggerCollection,
  triggerCollectionService,
  updateCredential,
  updateIP,
  updateSettingsBatch,
} from '@/lib/api';

const configurationTests = () => {
  it('allows the backend collection timeout plus response headroom', () => {
    expect(getMocks().create).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ timeout: 420_000 })
    );
  });
};

export const registerApiConfigurationTests = () =>
  describe('collection API configuration', configurationTests);

const endpointTests = () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('maps stats and status endpoints', async () => {
    getMocks()
      .apiInstance.get.mockResolvedValueOnce({ data: { success: true } })
      .mockResolvedValueOnce({ data: { success: true } });
    await getStats();
    await getSystemStatus();
    expect(getMocks().apiInstance.get).toHaveBeenNthCalledWith(1, '/dashboard/stats');
    expect(getMocks().apiInstance.get).toHaveBeenNthCalledWith(2, '/dashboard/status');
  });

  it('maps list retrieval endpoints with optional query params', async () => {
    getMocks().apiInstance.get.mockResolvedValue({ data: { success: true } });
    await getWhitelist();
    await getWhitelist('page=2&limit=20');
    await getCollectionHistory();
    await getCollectionHistory('page=3');
    await getBlacklist();
    await getBlacklist('page=5');
    await getFortinetPullLogs();
    await getFortinetPullLogs('service=regtech');
    await getUnifiedIPs();
    await getUnifiedIPs('ip=1.1.1.1');
    expect(getMocks().apiInstance.get).toHaveBeenNthCalledWith(1, '/ip-management/whitelist');
    expect(getMocks().apiInstance.get).toHaveBeenNthCalledWith(
      2,
      '/ip-management/whitelist?page=2&limit=20'
    );
    expect(getMocks().apiInstance.get).toHaveBeenNthCalledWith(3, '/collection/history');
    expect(getMocks().apiInstance.get).toHaveBeenNthCalledWith(4, '/collection/history?page=3');
    expect(getMocks().apiInstance.get).toHaveBeenNthCalledWith(5, '/ip-management/blacklist');
    expect(getMocks().apiInstance.get).toHaveBeenNthCalledWith(
      6,
      '/ip-management/blacklist?page=5'
    );
    expect(getMocks().apiInstance.get).toHaveBeenNthCalledWith(7, '/fortinet/pull-logs');
    expect(getMocks().apiInstance.get).toHaveBeenNthCalledWith(
      8,
      '/fortinet/pull-logs?service=regtech'
    );
    expect(getMocks().apiInstance.get).toHaveBeenNthCalledWith(9, '/ip-management/unified');
    expect(getMocks().apiInstance.get).toHaveBeenNthCalledWith(
      10,
      '/ip-management/unified?ip=1.1.1.1'
    );
  });

  it('maps single-resource and analytics endpoints', async () => {
    const mocks = getMocks();
    mocks.apiInstance.get.mockResolvedValue({ data: { success: true } });
    await getCollectionStatus();
    await searchIP('8.8.8.8');
    await getCollectionStatistics();
    await getBlacklistStats();
    await getCredential('regtech');
    await getDatabaseTables();
    await getDatabaseSchema();
    await getDailyDetectionStats();
    await getDailyDetectionStats(7);
    await getSettingsGrouped();
    await getCloudflareCredentials();
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(1, '/collection/status');
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(2, '/search/8.8.8.8');
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(3, '/collection/statistics');
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(4, '/collection/statistics');
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(5, '/collection/credentials/regtech');
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(6, '/database/tables');
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(7, '/schema');
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(
      8,
      '/analytics/detection-timeline?days=30'
    );
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(
      9,
      '/analytics/detection-timeline?days=7'
    );
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(10, '/settings/grouped');
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(11, '/collection/credentials/cloudflare');
  });

  it('maps mutating endpoints', async () => {
    const mocks = getMocks();
    mocks.apiInstance.post.mockResolvedValue({ data: { success: true } });
    mocks.apiInstance.put.mockResolvedValue({ data: { success: true } });
    mocks.apiInstance.delete.mockResolvedValue({ data: { success: true } });
    mocks.collectionInstance.post.mockResolvedValue({ data: { success: true } });
    await testCredential('regtech');
    await addIP('whitelist', { ip_address: '1.2.3.4', reason: 'manual' });
    await updateIP('blacklist', 9, { reason: 'updated' });
    await deleteIP('blacklist', 11);
    await updateCredential('regtech', { username: 'user' });
    await updateSettingsBatch([{ key: 'a', value: 'b' }]);
    await saveCloudflareCredentials({
      api_token: '••••••••',
      account_id: 'acct-1',
      list_id: 'list-1',
    });
    await testCloudflareConnection();
    await triggerCollection('2026-01-01', '2026-01-31');
    await triggerCollectionService('regtech', { force: true });
    expect(mocks.apiInstance.post).toHaveBeenNthCalledWith(
      1,
      '/collection/credentials/regtech/test'
    );
    expect(mocks.apiInstance.post).toHaveBeenNthCalledWith(2, '/ip-management/whitelist', {
      ip_address: '1.2.3.4',
      reason: 'manual',
    });
    expect(mocks.apiInstance.post).toHaveBeenNthCalledWith(
      3,
      '/collection/credentials/cloudflare/test'
    );
    expect(mocks.apiInstance.put).toHaveBeenNthCalledWith(1, '/ip-management/blacklist/9', {
      reason: 'updated',
    });
    expect(mocks.apiInstance.put).toHaveBeenNthCalledWith(2, '/collection/credentials/regtech', {
      username: 'user',
    });
    expect(mocks.apiInstance.put).toHaveBeenNthCalledWith(3, '/settings/batch', {
      settings: [{ key: 'a', value: 'b' }],
    });
    expect(mocks.apiInstance.put).toHaveBeenNthCalledWith(4, '/collection/credentials/cloudflare', {
      username: 'cloudflare-api',
      password: '***masked***',
      account_id: 'acct-1',
      list_id: 'list-1',
    });
    expect(mocks.apiInstance.delete).toHaveBeenCalledWith('/ip-management/blacklist/11');
    expect(mocks.collectionInstance.post).toHaveBeenNthCalledWith(
      1,
      '/collection/trigger/regtech',
      { start_date: '2026-01-01', end_date: '2026-01-31' }
    );
    expect(mocks.collectionInstance.post).toHaveBeenNthCalledWith(
      2,
      '/collection/trigger/regtech',
      { force: true }
    );
  });

  it('maps blob export and fortinet blocklist response shape', async () => {
    const mocks = getMocks();
    const blob = new Blob(['ip_address']);
    mocks.apiInstance.get.mockResolvedValueOnce({ data: blob }).mockResolvedValueOnce({
      data: { success: true, data: { blocklist: '1.1.1.1' } },
      headers: { 'content-type': 'application/json' },
    });
    const exportResult = await exportBlacklistRaw('type=blacklist');
    const blocklistResult = await getFortinetBlocklist();
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(
      1,
      '/blacklist/export-raw?type=blacklist',
      { responseType: 'blob' }
    );
    expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(2, '/fortinet/blocklist?format=json');
    expect(exportResult).toBe(blob);
    expect(blocklistResult).toEqual({
      data: { success: true, data: { blocklist: '1.1.1.1' } },
      headers: { 'content-type': 'application/json' },
    });
  });
};

export const registerApiEndpointTests = () => describe('API endpoint mapping', endpointTests);
