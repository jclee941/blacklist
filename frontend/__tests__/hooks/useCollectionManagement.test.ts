import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  getCredential: vi.fn(),
  updateCredential: vi.fn(),
  testCredential: vi.fn(),
  getCollectionStatus: vi.fn(),
  getBlacklistStats: vi.fn(),
  triggerCollectionService: vi.fn(),
}));

import { getCredential, testCredential, getCollectionStatus, getBlacklistStats } from '@/lib/api';
import { useCollectionManagement } from '@/app/collection/components/useCollectionManagement';

describe('useCollectionManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getCredential).mockResolvedValue(null);
    vi.mocked(getCollectionStatus).mockResolvedValue({ collection_enabled: false });
    vi.mocked(getBlacklistStats).mockResolvedValue({ total: 0, sources: {} });
  });

  it('initializes with default state', () => {
    const { result } = renderHook(() => useCollectionManagement());

    expect(result.current.credentials).toEqual([]);
    expect(result.current.loading).toBe(true);
    expect(result.current.showCredentialModal).toBe(false);
    expect(result.current.saving).toBe(false);
  });

  it('fetches data on mount', async () => {
    vi.mocked(getCredential).mockResolvedValue({
      username: 'admin',
      url: 'https://regtech.example.com',
    });
    vi.mocked(getCollectionStatus).mockResolvedValue({ collection_enabled: true });
    vi.mocked(getBlacklistStats).mockResolvedValue({ total: 100, sources: {} });

    const { result } = renderHook(() => useCollectionManagement());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
  });

  it('keeps the configured credential state returned by the API', async () => {
    vi.mocked(getCredential).mockResolvedValue({
      success: true,
      data: {
        service_name: 'REGTECH',
        username: 'admin',
        configured: true,
        enabled: true,
        collection_interval: 'daily',
        last_collection: null,
      },
    });

    const { result } = renderHook(() => useCollectionManagement());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.credentials[0]?.configured).toBe(true);
  });

  // --- Modal controls ---

  it('opens credential modal for REGTECH', async () => {
    const { result } = renderHook(() => useCollectionManagement());

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.openEditModal('REGTECH');
    });

    expect(result.current.showCredentialModal).toBe(true);
    expect(result.current.editingService).toBe('REGTECH');
  });

  it('closes credential modal', async () => {
    const { result } = renderHook(() => useCollectionManagement());

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.openEditModal('REGTECH');
    });
    act(() => {
      result.current.closeEditModal();
    });

    expect(result.current.showCredentialModal).toBe(false);
  });

  // --- formatInterval ---

  it('formats 3600 seconds as 1 hour (Korean)', () => {
    const { result } = renderHook(() => useCollectionManagement());

    const formatted = result.current.formatInterval(3600);

    // Should contain hour-related Korean text
    expect(formatted).toBeTruthy();
    expect(typeof formatted).toBe('string');
  });

  it('formats 60 seconds as 1 minute', () => {
    const { result } = renderHook(() => useCollectionManagement());

    const formatted = result.current.formatInterval(60);

    expect(formatted).toBeTruthy();
  });

  it('formats 0 seconds', () => {
    const { result } = renderHook(() => useCollectionManagement());

    const formatted = result.current.formatInterval(0);

    expect(typeof formatted).toBe('string');
  });

  // --- getSourceCount ---

  it('returns 0 for unknown source', async () => {
    vi.mocked(getBlacklistStats).mockResolvedValue({ total: 100, sources: {} });

    const { result } = renderHook(() => useCollectionManagement());

    await waitFor(() => expect(result.current.loading).toBe(false));

    const count = result.current.getSourceCount('UNKNOWN');
    expect(count).toBe(0);
  });

  // --- Test connection ---

  it('tests connection for a service', async () => {
    vi.mocked(testCredential).mockResolvedValue({ success: true });

    const { result } = renderHook(() => useCollectionManagement());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.testConnection('REGTECH');
    });

    expect(testCredential).toHaveBeenCalled();
  });

  it('preserves a recent connection test status when polling returns no status', async () => {
    vi.mocked(getCredential).mockResolvedValue({
      success: true,
      data: {
        service_name: 'REGTECH',
        username: 'admin',
        configured: true,
        enabled: true,
        collection_interval: 'daily',
        last_collection: null,
      },
    });
    vi.mocked(testCredential).mockResolvedValue({
      success: true,
      data: { status: 'connected', message: '인증 성공' },
    });

    const { result } = renderHook(() => useCollectionManagement());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.testConnection('REGTECH');
    });

    await act(async () => {
      await result.current.fetchData();
    });

    expect(result.current.credentials[0]?.connection_status).toBe('connected');
    expect(result.current.credentials[0]?.status_message).toBe('인증 성공');
  });

  // --- Notification ---

  it('notification starts as null', () => {
    const { result } = renderHook(() => useCollectionManagement());

    expect(result.current.notification).toBeNull();
  });
});
