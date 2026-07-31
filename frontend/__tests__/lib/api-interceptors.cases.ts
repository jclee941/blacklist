import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getMocks, getResponseErrorHandler } from './api-test-helpers';
import { AUTH_UNAUTHORIZED_EVENT, getStats, getToken, setToken } from '@/lib/api';

type RequestConfig = { headers: Record<string, string> };
type RequestInterceptor = (config: RequestConfig) => RequestConfig;

const responseErrorHandler = getResponseErrorHandler();
let requestCb: RequestInterceptor | undefined;

const getRequestInterceptor = (): RequestInterceptor => {
  const callback = getMocks().apiInstance.interceptors.request.use.mock.calls[0]?.[0];
  if (typeof callback !== 'function') {
    throw new Error('request interceptor was not registered');
  }
  return callback;
};

const resetInterceptorState = () => {
  localStorage.clear();
  vi.clearAllMocks();
};

export const registerApiInterceptorTests = () => {
  describe('interceptors', () => {
    beforeEach(resetInterceptorState);

    it('registers request/response interceptors for both axios instances', async () => {
      vi.resetModules();
      const freshApiInstance = {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
        interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
      };
      const freshCollectionInstance = {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
        interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
      };
      vi.doMock('axios', () => ({
        default: {
          create: vi
            .fn()
            .mockReturnValueOnce(freshApiInstance)
            .mockReturnValueOnce(freshCollectionInstance),
          get: vi.fn(),
          isAxiosError: (error: unknown) =>
            typeof error === 'object' && error !== null && 'response' in error,
        },
      }));
      await import('@/lib/api');
      expect(freshApiInstance.interceptors.request.use).toHaveBeenCalledTimes(1);
      expect(freshCollectionInstance.interceptors.request.use).toHaveBeenCalledTimes(1);
      expect(freshApiInstance.interceptors.response.use).toHaveBeenCalledTimes(1);
      expect(freshCollectionInstance.interceptors.response.use).toHaveBeenCalledTimes(1);
      const callback = freshApiInstance.interceptors.request.use.mock.calls[0]?.[0];
      if (typeof callback !== 'function') {
        throw new Error('fresh request interceptor was not registered');
      }
      requestCb = callback;
    });

    it('attaches Bearer token when token exists', () => {
      const callback = requestCb ?? getRequestInterceptor();
      setToken('token-xyz');
      const config = callback({ headers: {} });
      expect(config.headers.Authorization).toBe('Bearer token-xyz');
    });

    it('does not attach authorization header when token is missing', () => {
      const callback = requestCb ?? getRequestInterceptor();
      const config = callback({ headers: {} });
      expect(config.headers.Authorization).toBeUndefined();
    });

    it('clears the token and notifies the application after a protected 401 response', async () => {
      const error = { response: { status: 401 }, config: { url: '/web-stats' } };
      const unauthorizedListener = vi.fn();
      setToken('expired-token');
      window.addEventListener(AUTH_UNAUTHORIZED_EVENT, unauthorizedListener);
      await expect(responseErrorHandler(error)).rejects.toBe(error);
      expect(getToken()).toBeNull();
      expect(unauthorizedListener).toHaveBeenCalledTimes(1);
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, unauthorizedListener);
    });

    it('keeps the stored token for a failed login response', async () => {
      const error = { response: { status: 401 }, config: { url: '/auth/login' } };
      setToken('existing-token');
      await expect(responseErrorHandler(error)).rejects.toBe(error);
      expect(getToken()).toBe('existing-token');
    });
  });
};

export const registerApiErrorTests = () => {
  describe('error handling', () => {
    beforeEach(resetInterceptorState);

    it('propagates request errors', async () => {
      const error = new Error('network down');
      getMocks().apiInstance.get.mockRejectedValueOnce(error);
      await expect(getStats()).rejects.toThrow('network down');
    });
  });
};
