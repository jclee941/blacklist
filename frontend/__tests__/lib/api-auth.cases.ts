import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getMocks } from './api-test-helpers';
import { getToken, login, logout, removeToken, setToken, verifyToken } from '@/lib/api';

type ApiPayload = { success: boolean; data?: unknown; token?: string; error?: string };

const resetAuthState = () => {
  localStorage.clear();
  vi.clearAllMocks();
};

export const registerApiTokenTests = () => {
  describe('token management', () => {
    beforeEach(resetAuthState);

    it('handles token CRUD in localStorage', () => {
      expect(getToken()).toBeNull();
      setToken('jwt-123');
      expect(getToken()).toBe('jwt-123');
      removeToken();
      expect(getToken()).toBeNull();
    });
  });
};

export const registerApiAuthFlowTests = () => {
  describe('auth flow', () => {
    beforeEach(resetAuthState);

    it('login posts credentials and stores token', async () => {
      const response: ApiPayload = { success: true, token: 'new-token' };
      getMocks().apiInstance.post.mockResolvedValueOnce({ data: response });
      const data = await login('admin', 'pw1234');
      expect(getMocks().apiInstance.post).toHaveBeenCalledWith('/auth/login', {
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
      getMocks().apiInstance.get.mockResolvedValueOnce({ data: response });
      await expect(verifyToken()).resolves.toEqual(response);
      expect(getMocks().apiInstance.get).toHaveBeenCalledWith('/auth/verify');
    });
  });
};
