import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getMocks } from './api-test-helpers';
import { login, logout, verifyToken } from '@/lib/api';

type ApiPayload = { success: boolean; data?: unknown; token?: string; error?: string };

const resetAuthState = () => {
  localStorage.clear();
  vi.clearAllMocks();
};

export const registerApiTokenTests = () => {
  describe('token management', () => {
    beforeEach(resetAuthState);

    it('never persists the session token in browser storage', async () => {
      getMocks().apiInstance.post.mockResolvedValueOnce({
        data: { success: true, token: 'server-issued-token' },
      });

      await login('admin', 'pw1234');

      expect(localStorage.length).toBe(0);
    });
  });
};

export const registerApiAuthFlowTests = () => {
  describe('auth flow', () => {
    beforeEach(resetAuthState);

    it('login posts credentials and leaves the session to the server cookie', async () => {
      const response: ApiPayload = { success: true, token: 'new-token' };
      getMocks().apiInstance.post.mockResolvedValueOnce({ data: response });
      const data = await login('admin', 'pw1234');
      expect(getMocks().apiInstance.post).toHaveBeenCalledWith('/auth/login', {
        username: 'admin',
        password: 'pw1234',
      });
      expect(data).toEqual(response);
    });

    it('logout revokes the session on the server', async () => {
      getMocks().apiInstance.post.mockResolvedValueOnce({ data: { success: true } });
      await logout();
      expect(getMocks().apiInstance.post).toHaveBeenCalledWith('/auth/logout');
    });

    it('logout resolves when server revocation fails', async () => {
      getMocks().apiInstance.post.mockRejectedValueOnce(new Error('network unavailable'));
      await expect(logout()).resolves.toBeUndefined();
    });

    it('verifyToken uses auth verify endpoint', async () => {
      const response: ApiPayload = { success: true, data: { valid: true } };
      getMocks().apiInstance.get.mockResolvedValueOnce({ data: response });
      await expect(verifyToken()).resolves.toEqual(response);
      expect(getMocks().apiInstance.get).toHaveBeenCalledWith('/auth/verify');
    });
  });
};
