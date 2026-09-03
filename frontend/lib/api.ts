import axios from 'axios';
import type { CredentialPayload, IPPayload } from '@/types';

const TOKEN_KEY = 'blacklist_auth_token';
const LOGIN_ENDPOINT = '/auth/login';
export const AUTH_UNAUTHORIZED_EVENT = 'blacklist:auth-unauthorized';

export const getToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
};

export const setToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const removeToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
};

// API 클라이언트 설정 - Next.js Rewrites 사용
const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-store',
    Pragma: 'no-cache',
    Expires: '0',
  },
});

export const collectionApi = axios.create({
  baseURL: '/api',
  timeout: 420_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

const attachToken = (config: import('axios').InternalAxiosRequestConfig) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

api.interceptors.request.use(attachToken);
collectionApi.interceptors.request.use(attachToken);

const handleResponseError = (error: unknown): Promise<never> => {
  if (
    axios.isAxiosError(error) &&
    error.response?.status === 401 &&
    error.config?.url !== LOGIN_ENDPOINT
  ) {
    removeToken();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
    }
  }
  return Promise.reject(error);
};

api.interceptors.response.use((response) => response, handleResponseError);
collectionApi.interceptors.response.use((response) => response, handleResponseError);

export const login = async (username: string, password: string) => {
  const { data } = await api.post(LOGIN_ENDPOINT, { username, password });
  if (data.token) {
    setToken(data.token);
  }
  return data;
};

export const logout = async (): Promise<void> => {
  try {
    if (getToken()) {
      await api.post('/auth/logout');
    }
  } catch (error) {
    if (!(error instanceof Error)) {
      throw error;
    }
  } finally {
    removeToken();
  }
};

export const verifyToken = async () => {
  const { data } = await api.get('/auth/verify');
  return data;
};

export const getStats = async () => {
  const { data } = await api.get('/dashboard/stats');
  return data;
};

export const getSystemStatus = async () => {
  const { data } = await api.get('/dashboard/status');
  return data;
};

export const getWhitelist = async (params?: string) => {
  const url = params ? `/ip-management/whitelist?${params}` : '/ip-management/whitelist';
  const { data } = await api.get(url);
  return data;
};

export const getCollectionStatus = async () => {
  const { data } = await api.get('/proxy/collection/status');
  return data;
};

export const searchIP = async (ip: string) => {
  const { data } = await api.get(`/search/${ip}`);
  return data;
};

export const getCollectionHistory = async (params?: string) => {
  const url = params ? `/proxy/collection/history?${params}` : '/proxy/collection/history';
  const { data } = await api.get(url);
  return data;
};

export const getCollectionStatistics = async () => {
  const { data } = await api.get('/proxy/collection/statistics');
  return data;
};

export const getBlacklist = async (params?: string) => {
  const url = params ? `/ip-management/blacklist?${params}` : '/ip-management/blacklist';
  const { data } = await api.get(url);
  return data;
};

export const getBlacklistStats = async () => {
  const { data } = await api.get('/collection/statistics');
  return data;
};

export const getCredential = async (source: string) => {
  const { data } = await api.get(`/proxy/collection/credentials/${source}`);
  return data;
};

export const updateCredential = async (source: string, credentialData: CredentialPayload) => {
  const { data } = await api.put(`/proxy/collection/credentials/${source}`, credentialData);
  return data;
};

export const testCredential = async (source: string) => {
  const { data } = await api.post(`/proxy/collection/credentials/${source}/test`);
  return data;
};

export const getDatabaseTables = async () => {
  const { data } = await api.get('/database/tables');
  return data;
};

export const getDatabaseSchema = async () => {
  const { data } = await api.get('/schema');
  return data;
};

export const getFortinetPullLogs = async (params?: string) => {
  const url = params ? `/fortinet/pull-logs?${params}` : '/fortinet/pull-logs';
  const { data } = await api.get(url);
  return data;
};

export const getFortinetBlocklist = async (): Promise<{
  data:
    | string
    | {
        success: boolean;
        data?: { blocklist?: string; total?: number };
        blocklist?: string;
        error?: string;
      };
  headers: Record<string, string>;
}> => {
  const response = await api.get('/fortinet/blocklist?format=json');
  return { data: response.data, headers: response.headers as Record<string, string> };
};

export const getUnifiedIPs = async (params?: string) => {
  const url = params ? `/ip-management/unified?${params}` : '/ip-management/unified';
  const { data } = await api.get(url);
  return data;
};

export const addIP = async (type: 'whitelist' | 'blacklist', payload: IPPayload) => {
  const { data } = await api.post(`/ip-management/${type}`, payload);
  return data;
};

export const updateIP = async (
  type: 'whitelist' | 'blacklist',
  id: number,
  payload: Partial<IPPayload>
) => {
  const { data } = await api.put(`/ip-management/${type}/${id}`, payload);
  return data;
};

export const deleteIP = async (type: 'whitelist' | 'blacklist', id: number) => {
  const { data } = await api.delete(`/ip-management/${type}/${id}`);
  return data;
};

export const exportBlacklistRaw = async (params?: string) => {
  const url = params ? `/blacklist/export-raw?${params}` : '/blacklist/export-raw';
  const response = await api.get(url, {
    responseType: 'blob',
  });
  return response.data;
};

export const triggerCollection = async (startDate: string, endDate: string) => {
  const { data } = await collectionApi.post('/proxy/collection/trigger/regtech', {
    start_date: startDate,
    end_date: endDate,
  });
  return data;
};

export const triggerCollectionService = async (
  serviceName: string,
  options?: { force?: boolean }
) => {
  const { data } = await collectionApi.post(
    `/proxy/collection/trigger/${serviceName}`,
    options || {}
  );
  return data;
};

export const getDailyDetectionStats = async (days: number = 30) => {
  const { data } = await api.get(`/analytics/detection-timeline?days=${days}`);
  return data;
};

export const getSettingsGrouped = async () => {
  const { data } = await api.get('/settings/grouped');
  return data;
};

export const updateSettingsBatch = async (settings: { key: string; value: string }[]) => {
  const { data } = await api.put('/settings/batch', { settings });
  return data;
};

export const getCloudflareCredentials = async () => {
  const { data } = await api.get('/proxy/collection/credentials/cloudflare');
  return data;
};

export const saveCloudflareCredentials = async (payload: {
  api_token: string;
  account_id: string;
  list_id: string;
}) => {
  const password = payload.api_token === '••••••••' ? '***masked***' : payload.api_token;
  const { data } = await api.put('/proxy/collection/credentials/cloudflare', {
    username: 'cloudflare-api',
    password,
    account_id: payload.account_id,
    list_id: payload.list_id,
  });
  return data;
};

export const testCloudflareConnection = async () => {
  const { data } = await api.post('/proxy/collection/credentials/cloudflare/test');
  return data;
};

export default api;
