import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

vi.mock('@/lib/api', () => ({
  getStats: vi.fn(),
  getHealth: vi.fn(),
  getCollectionHistory: vi.fn(),
  getAuthStatus: vi.fn(),
}));

import { getStats, getHealth, getCollectionHistory, getAuthStatus } from '@/lib/api';
import { useStats, useHealth, useCollectionHistory, useAuthStatus } from '@/hooks/useStats';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  }
  Wrapper.displayName = 'QueryWrapper';
  return Wrapper;
}

describe('useStats', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches stats data', async () => {
    const mockData = { total: 100, active: 80 };
    vi.mocked(getStats).mockResolvedValue(mockData);

    const { result } = renderHook(() => useStats(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockData);
  });

  it('handles stats error', async () => {
    vi.mocked(getStats).mockRejectedValue(new Error('API Error'));

    const { result } = renderHook(() => useStats(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it('starts in loading state', () => {
    vi.mocked(getStats).mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useStats(), { wrapper: createWrapper() });

    expect(result.current.isLoading).toBe(true);
  });
});

describe('useHealth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches health data', async () => {
    const mockData = { status: 'healthy', uptime: 12345 };
    vi.mocked(getHealth).mockResolvedValue(mockData);

    const { result } = renderHook(() => useHealth(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockData);
  });

  it('handles health error', async () => {
    vi.mocked(getHealth).mockRejectedValue(new Error('Unreachable'));

    const { result } = renderHook(() => useHealth(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useCollectionHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches collection history', async () => {
    const mockData = [{ date: '2025-01-15', count: 50 }];
    vi.mocked(getCollectionHistory).mockResolvedValue(mockData);

    const { result } = renderHook(() => useCollectionHistory(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockData);
  });

  it('handles history error', async () => {
    vi.mocked(getCollectionHistory).mockRejectedValue(new Error('Timeout'));

    const { result } = renderHook(() => useCollectionHistory(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useAuthStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches auth status', async () => {
    const mockData = { authenticated: true, user: 'admin' };
    vi.mocked(getAuthStatus).mockResolvedValue(mockData);

    const { result } = renderHook(() => useAuthStatus(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockData);
  });

  it('handles auth error', async () => {
    vi.mocked(getAuthStatus).mockRejectedValue(new Error('Unauthorized'));

    const { result } = renderHook(() => useAuthStatus(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
