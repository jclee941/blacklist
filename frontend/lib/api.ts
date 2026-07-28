import axios from 'axios';
import type { CredentialPayload, IPPayload } from '@/types';

// JWT token management
const TOKEN_KEY = 'blacklist_auth_token';
const LOGIN_ENDPOINT = '/auth/login';

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

// 수집 API 전용 인스턴스
export const collectionApi = axios.create({
  baseURL: '/api',
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach JWT token
const attachToken = (config: import('axios').InternalAxiosRequestConfig) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

api.interceptors.request.use(attachToken);
collectionApi.interceptors.request.use(attachToken);

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(error)
);
collectionApi.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(error)
);

// 인증 API
export const login = async (username: string, password: string) => {
  const { data } = await api.post(LOGIN_ENDPOINT, { username, password });
  if (data.token) {
    setToken(data.token);
  }
  return data;
};

export const logout = () => {
  removeToken();
};

export const verifyToken = async () => {
  const { data } = await api.get('/auth/verify');
  return data;
};

// 통계 API
export const getStats = async () => {
  const { data } = await api.get('/web-stats');
  return data;
};

// 시스템 상태 API (Dashboard)
export const getSystemStatus = async () => {
  const { data } = await api.get('/connection/status');
  return data;
};

// 화이트리스트 조회 API
export const getWhitelist = async (params?: string) => {
  const url = params ? `/ip-management/whitelist?${params}` : '/ip-management/whitelist';
  const { data } = await api.get(url);
  return data;
};

// 수집 상태 API
export const getCollectionStatus = async () => {
  const { data } = await api.get('/proxy/collection/status');
  return data;
};

// IP 검색 API
export const searchIP = async (ip: string) => {
  const { data } = await api.get(`/search/${ip}`);
  return data;
};

// 수집 내역 API
export const getCollectionHistory = async (params?: string) => {
  const url = params ? `/proxy/collection/history?${params}` : '/proxy/collection/history';
  const { data } = await api.get(url);
  return data;
};

// 수집 통계 API
export const getCollectionStatistics = async () => {
  const { data } = await api.get('/proxy/collection/statistics');
  return data;
};

// 블랙리스트 목록 조회 API
export const getBlacklist = async (params?: string) => {
  const url = params ? `/ip-management/blacklist?${params}` : '/ip-management/blacklist';
  const { data } = await api.get(url);
  return data;
};

// 블랙리스트 통계 API
export const getBlacklistStats = async () => {
  const { data } = await api.get('/collection/statistics');
  return data;
};

// 인증정보 조회 API
export const getCredential = async (source: string) => {
  const { data } = await api.get(`/proxy/collection/credentials/${source}`);
  return data;
};

// 인증정보 수정 API
export const updateCredential = async (source: string, credentialData: CredentialPayload) => {
  const { data } = await api.put(`/proxy/collection/credentials/${source}`, credentialData);
  return data;
};

// 인증정보 연결 테스트 API
export const testCredential = async (source: string) => {
  const { data } = await api.post(`/proxy/collection/credentials/${source}/test`);
  return data;
};

// 데이터베이스 테이블 목록 API
export const getDatabaseTables = async () => {
  const { data } = await api.get('/database/tables');
  return data;
};

// 데이터베이스 스키마 조회 API
export const getDatabaseSchema = async () => {
  const { data } = await api.get('/schema');
  return data;
};

// Fortinet 로그 조회 API
export const getFortinetPullLogs = async (params?: string) => {
  const url = params ? `/fortinet/pull-logs?${params}` : '/fortinet/pull-logs';
  const { data } = await api.get(url);
  return data;
};

// Fortinet 차단 목록 조회 API
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

// IP 추가 API
export const addIP = async (type: 'whitelist' | 'blacklist', payload: IPPayload) => {
  const { data } = await api.post(`/ip-management/${type}`, payload);
  return data;
};

// IP 수정 API
export const updateIP = async (
  type: 'whitelist' | 'blacklist',
  id: number,
  payload: Partial<IPPayload>
) => {
  const { data } = await api.put(`/ip-management/${type}/${id}`, payload);
  return data;
};

// IP 삭제 API
export const deleteIP = async (type: 'whitelist' | 'blacklist', id: number) => {
  const { data } = await api.delete(`/ip-management/${type}/${id}`);
  return data;
};

// Raw 데이터 내보내기 API
export const exportBlacklistRaw = async (params?: string) => {
  const url = params ? `/blacklist/export-raw?${params}` : '/blacklist/export-raw';
  const response = await api.get(url, {
    responseType: 'blob', // 파일 다운로드를 위해 blob으로 설정
  });
  return response.data; // Blob 반환
};

// 수집 트리거 API
export const triggerCollection = async (startDate: string, endDate: string) => {
  const { data } = await collectionApi.post('/proxy/collection/trigger/regtech', {
    start_date: startDate,
    end_date: endDate,
  });
  return data;
};

// 서비스별 수집 트리거 API
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

// 시스템 상태 API
export const getHealth = async () => {
  const { data } = await axios.get('/health');
  return data;
};

// 인증 상태 API
export const getAuthStatus = async () => {
  const { data } = await api.get('/proxy/collection/credentials/regtech');
  return data;
};

// 일별 탐지 통계 API
export const getDailyDetectionStats = async (days: number = 30) => {
  const { data } = await api.get(`/analytics/detection-timeline?days=${days}`);
  return data;
};

// 설정 API
export const getSettingsGrouped = async () => {
  const { data } = await api.get('/settings/grouped');
  return data;
};

export const updateSettingsBatch = async (settings: { key: string; value: string }[]) => {
  const { data } = await api.put('/settings/batch', { settings });
  return data;
};

// Cloudflare credential management
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
