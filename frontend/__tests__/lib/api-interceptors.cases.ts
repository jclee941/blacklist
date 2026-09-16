import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getMocks, getResponseErrorHandler } from './api-test-helpers';
import { AUTH_UNAUTHORIZED_EVENT, getStats } from '@/lib/api';

const responseErrorHandler = getResponseErrorHandler();

const resetInterceptorState = () => {
  localStorage.clear();
  vi.clearAllMocks();
};

export const registerApiInterceptorTests = () => {
  describe('interceptors', () => {
    beforeEach(resetInterceptorState);

    it('registers response interceptors and attaches no token header', async () => {
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
      // The session cookie is attached by the browser, so no request interceptor runs.
      expect(freshApiInstance.interceptors.request.use).not.toHaveBeenCalled();
      expect(freshCollectionInstance.interceptors.request.use).not.toHaveBeenCalled();
      expect(freshApiInstance.interceptors.response.use).toHaveBeenCalledTimes(1);
      expect(freshCollectionInstance.interceptors.response.use).toHaveBeenCalledTimes(1);
    });

    it('notifies the application after a protected 401 response', async () => {
      const error = { response: { status: 401 }, config: { url: '/web-stats' } };
      const unauthorizedListener = vi.fn();
      window.addEventListener(AUTH_UNAUTHORIZED_EVENT, unauthorizedListener);
      await expect(responseErrorHandler(error)).rejects.toBe(error);
      expect(unauthorizedListener).toHaveBeenCalledTimes(1);
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, unauthorizedListener);
    });

    it('stays silent for a failed login response', async () => {
      const error = { response: { status: 401 }, config: { url: '/auth/login' } };
      const unauthorizedListener = vi.fn();
      window.addEventListener(AUTH_UNAUTHORIZED_EVENT, unauthorizedListener);
      await expect(responseErrorHandler(error)).rejects.toBe(error);
      expect(unauthorizedListener).not.toHaveBeenCalled();
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, unauthorizedListener);
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
