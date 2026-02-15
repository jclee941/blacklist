import { beforeEach, describe, expect, it, vi } from 'vitest';

type ApiPayload = { success: boolean; data?: unknown; token?: string; error?: string };

const mocks = vi.hoisted(() => {
  const apiInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };

  const collectionInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };

  const axiosGet = vi.fn();

  return { apiInstance, collectionInstance, axiosGet };
});

vi.mock('axios', () => {
  const create = vi
    .fn()
    .mockReturnValueOnce(mocks.apiInstance)
    .mockReturnValueOnce(mocks.collectionInstance);

  return {
    default: {
      create,
      get: mocks.axiosGet,
    },
  };
});

import {
  addIP,
  deleteIP,
  exportBlacklistRaw,
  getAuthStatus,
  getBlacklist,
  getBlacklistStats,
  getCollectionHistory,
  getCollectionStatistics,
  getCollectionStatus,
  getCredential,
  getDailyDetectionStats,
  getDatabaseSchema,
  getDatabaseTables,
  getFortinetBlocklist,
  getFortinetPullLogs,
  getHealth,
  getSettingsGrouped,
  getStats,
  getSystemStatus,
  getToken,
  getUnifiedIPs,
  getWhitelist,
  login,
  logout,
  removeToken,
  searchIP,
  setToken,
  testCredential,
  triggerCollection,
  triggerCollectionService,
  updateCredential,
  updateIP,
  updateSettingsBatch,
  verifyToken,
} from '@/lib/api';

describe('lib/api', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('token management', () => {
    it('handles token CRUD in localStorage', () => {
      expect(getToken()).toBeNull();

      setToken('jwt-123');
      expect(getToken()).toBe('jwt-123');

      removeToken();
      expect(getToken()).toBeNull();
    });
  });

  describe('interceptors', () => {
    // Interceptors are registered at module load time (before beforeEach clears mocks).
    // We capture the callback references once and reuse them.
    let requestCb:
      | ((config: { headers: Record<string, string> }) => {
          headers: Record<string, string>;
        })
      | undefined;

    it('registers request/response interceptors for both axios instances', () => {
      // Interceptor registration happened at import time.
      // After beforeEach clears mocks the call counts are reset,
      // so we re-import the module to trigger fresh registration.
      vi.resetModules();

      // Recreate mock state before re-import
      const freshApiInstance = {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() },
        },
      };
      const freshCollectionInstance = {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() },
        },
      };

      vi.doMock('axios', () => ({
        default: {
          create: vi
            .fn()
            .mockReturnValueOnce(freshApiInstance)
            .mockReturnValueOnce(freshCollectionInstance),
          get: vi.fn(),
        },
      }));

      // Dynamic import triggers module-level code
      return import('@/lib/api').then(() => {
        expect(freshApiInstance.interceptors.request.use).toHaveBeenCalledTimes(1);
        expect(freshCollectionInstance.interceptors.request.use).toHaveBeenCalledTimes(1);
        expect(freshApiInstance.interceptors.response.use).toHaveBeenCalledTimes(1);
        expect(freshCollectionInstance.interceptors.response.use).toHaveBeenCalledTimes(1);

        // Capture the request callback for later tests
        requestCb = freshApiInstance.interceptors.request.use.mock
          .calls[0]?.[0] as typeof requestCb;
      });
    });

    it('attaches Bearer token when token exists', () => {
      // If the capture from previous test is available, use it; otherwise skip gracefully.
      if (!requestCb) {
        // Fallback: try to read from the hoisted mocks (module-load registration)
        const calls = mocks.apiInstance.interceptors.request.use.mock.calls;
        if (calls.length > 0) {
          requestCb = calls[0][0] as typeof requestCb;
        }
      }
      expect(requestCb).toBeDefined();
      setToken('token-xyz');

      const config = requestCb!({ headers: {} });
      expect(config.headers.Authorization).toBe('Bearer token-xyz');
    });

    it('does not attach authorization header when token is missing', () => {
      if (!requestCb) {
        const calls = mocks.apiInstance.interceptors.request.use.mock.calls;
        if (calls.length > 0) {
          requestCb = calls[0][0] as typeof requestCb;
        }
      }
      expect(requestCb).toBeDefined();

      const config = requestCb!({ headers: {} });
      expect(config.headers.Authorization).toBeUndefined();
    });
  });

  describe('auth flow', () => {
    it('login posts credentials and stores token', async () => {
      const response: ApiPayload = { success: true, token: 'new-token' };
      mocks.apiInstance.post.mockResolvedValueOnce({ data: response });

      const data = await login('admin', 'pw1234');

      expect(mocks.apiInstance.post).toHaveBeenCalledWith('/auth/login', {
        username: 'admin',
        password: 'pw1234',
      });
      expect(data).toEqual(response);
      expect(getToken()).toBe('new-token');
    });

    it('logout removes stored token', () => {
      setToken('temporary-token');
      logout();
      expect(getToken()).toBeNull();
    });

    it('verifyToken uses auth verify endpoint', async () => {
      const response: ApiPayload = { success: true, data: { valid: true } };
      mocks.apiInstance.get.mockResolvedValueOnce({ data: response });

      await expect(verifyToken()).resolves.toEqual(response);
      expect(mocks.apiInstance.get).toHaveBeenCalledWith('/auth/verify');
    });
  });

  describe('API endpoint mapping', () => {
    it('maps stats and status endpoints', async () => {
      mocks.apiInstance.get
        .mockResolvedValueOnce({ data: { success: true } })
        .mockResolvedValueOnce({ data: { success: true } });

      await getStats();
      await getSystemStatus();

      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(1, '/web-stats');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(2, '/connection/status');
    });

    it('maps list retrieval endpoints with optional query params', async () => {
      mocks.apiInstance.get.mockResolvedValue({ data: { success: true } });

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

      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(1, '/ip-management/whitelist');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(
        2,
        '/ip-management/whitelist?page=2&limit=20'
      );
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(3, '/proxy/collection/history');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(4, '/proxy/collection/history?page=3');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(5, '/ip-management/blacklist');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(6, '/ip-management/blacklist?page=5');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(7, '/fortinet/pull-logs');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(
        8,
        '/fortinet/pull-logs?service=regtech'
      );
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(9, '/ip-management/unified');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(
        10,
        '/ip-management/unified?ip=1.1.1.1'
      );
    });

    it('maps single-resource and analytics endpoints', async () => {
      mocks.apiInstance.get.mockResolvedValue({ data: { success: true } });

      await getCollectionStatus();
      await searchIP('8.8.8.8');
      await getCollectionStatistics();
      await getBlacklistStats();
      await getCredential('regtech');
      await getDatabaseTables();
      await getDatabaseSchema();
      await getAuthStatus();
      await getDailyDetectionStats();
      await getDailyDetectionStats(7);
      await getSettingsGrouped();

      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(1, '/proxy/collection/status');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(2, '/search/8.8.8.8');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(3, '/proxy/collection/statistics');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(4, '/collection/statistics');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(
        5,
        '/proxy/collection/credentials/regtech'
      );
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(6, '/database/tables');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(7, '/schema');
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(
        8,
        '/proxy/collection/credentials/regtech'
      );
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(
        9,
        '/analytics/detection-timeline?days=30'
      );
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(
        10,
        '/analytics/detection-timeline?days=7'
      );
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(11, '/settings/grouped');
    });

    it('maps mutating endpoints', async () => {
      mocks.apiInstance.post.mockResolvedValue({ data: { success: true } });
      mocks.apiInstance.put.mockResolvedValue({ data: { success: true } });
      mocks.apiInstance.delete.mockResolvedValue({ data: { success: true } });
      mocks.collectionInstance.post.mockResolvedValue({ data: { success: true } });

      await testCredential('regtech');
      await addIP('whitelist', { ip_address: '1.2.3.4', reason: 'manual' });
      await updateIP('blacklist', 9, { reason: 'updated' });
      await deleteIP('blacklist', 11);
      await updateCredential('secudium', { username: 'user' });
      await updateSettingsBatch([{ key: 'a', value: 'b' }]);
      await triggerCollection('2026-01-01', '2026-01-31');
      await triggerCollectionService('secudium');
      await triggerCollectionService('regtech', { force: true });

      expect(mocks.apiInstance.post).toHaveBeenNthCalledWith(
        1,
        '/proxy/collection/credentials/regtech/test'
      );
      expect(mocks.apiInstance.post).toHaveBeenNthCalledWith(2, '/ip-management/whitelist', {
        ip_address: '1.2.3.4',
        reason: 'manual',
      });

      expect(mocks.apiInstance.put).toHaveBeenNthCalledWith(1, '/ip-management/blacklist/9', {
        reason: 'updated',
      });
      expect(mocks.apiInstance.put).toHaveBeenNthCalledWith(
        2,
        '/proxy/collection/credentials/secudium',
        { username: 'user' }
      );
      expect(mocks.apiInstance.put).toHaveBeenNthCalledWith(3, '/settings/batch', {
        settings: [{ key: 'a', value: 'b' }],
      });
      expect(mocks.apiInstance.delete).toHaveBeenCalledWith('/ip-management/blacklist/11');

      expect(mocks.collectionInstance.post).toHaveBeenNthCalledWith(
        1,
        '/proxy/collection/trigger/regtech',
        {
          start_date: '2026-01-01',
          end_date: '2026-01-31',
        }
      );
      expect(mocks.collectionInstance.post).toHaveBeenNthCalledWith(
        2,
        '/proxy/collection/trigger/secudium',
        {}
      );
      expect(mocks.collectionInstance.post).toHaveBeenNthCalledWith(
        3,
        '/proxy/collection/trigger/regtech',
        { force: true }
      );
    });

    it('maps blob export and fortinet blocklist response shape', async () => {
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
        {
          responseType: 'blob',
        }
      );
      expect(mocks.apiInstance.get).toHaveBeenNthCalledWith(2, '/fortinet/blocklist?format=json');

      expect(exportResult).toBe(blob);
      expect(blocklistResult).toEqual({
        data: { success: true, data: { blocklist: '1.1.1.1' } },
        headers: { 'content-type': 'application/json' },
      });
    });

    it('uses top-level axios for health endpoint', async () => {
      mocks.axiosGet.mockResolvedValueOnce({ data: { status: 'ok' } });

      await expect(getHealth()).resolves.toEqual({ status: 'ok' });
      expect(mocks.axiosGet).toHaveBeenCalledWith('/health');
    });
  });

  describe('error handling', () => {
    it('propagates request errors', async () => {
      const error = new Error('network down');
      mocks.apiInstance.get.mockRejectedValueOnce(error);

      await expect(getStats()).rejects.toThrow('network down');
    });
  });
});
