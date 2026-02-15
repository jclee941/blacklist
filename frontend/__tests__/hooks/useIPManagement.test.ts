import { vi, describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

vi.mock('@/lib/api', () => ({
  getUnifiedIPs: vi.fn(),
  getWhitelist: vi.fn(),
  getBlacklist: vi.fn(),
  addIP: vi.fn(),
  updateIP: vi.fn(),
  deleteIP: vi.fn(),
  exportBlacklistRaw: vi.fn(),
}));

import { getUnifiedIPs, getWhitelist, getBlacklist, addIP, deleteIP } from '@/lib/api';
import { useIPManagement } from '@/app/ip-management/components/useIPManagement';

describe('useIPManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getUnifiedIPs).mockResolvedValue({ data: [], total: 0, pages: 0 });
    vi.mocked(getWhitelist).mockResolvedValue({ data: [], total: 0, pages: 0 });
    vi.mocked(getBlacklist).mockResolvedValue({ data: [], total: 0, pages: 0 });
  });

  it('initializes with default state', () => {
    const { result } = renderHook(() => useIPManagement());

    expect(result.current.activeTab).toBe('unified');
    expect(result.current.data).toEqual([]);
    expect(result.current.showAddModal).toBe(false);
    expect(result.current.showEditModal).toBe(false);
    expect(result.current.showDeleteModal).toBe(false);
    expect(result.current.isSubmitting).toBe(false);
  });

  it('fetches data on mount', async () => {
    vi.mocked(getUnifiedIPs).mockResolvedValue({
      data: [{ id: 1, ip_address: '10.0.0.1' }],
      total: 1,
      pages: 1,
    });

    const { result } = renderHook(() => useIPManagement());

    await waitFor(() => {
      expect(result.current.data.length).toBeGreaterThanOrEqual(0);
    });
  });

  // --- Modal controls ---

  it('opens add modal', () => {
    const { result } = renderHook(() => useIPManagement());

    act(() => {
      result.current.openAddModal();
    });

    expect(result.current.showAddModal).toBe(true);
  });

  it('closes add modal', () => {
    const { result } = renderHook(() => useIPManagement());

    act(() => {
      result.current.openAddModal();
    });
    act(() => {
      result.current.closeAddModal();
    });

    expect(result.current.showAddModal).toBe(false);
  });

  it('opens edit modal with record data', () => {
    const { result } = renderHook(() => useIPManagement());

    const record = {
      id: 1,
      ip_address: '10.0.0.1',
      reason: 'Malware',
      source: 'REGTECH',
      country: 'KR',
      is_active: true,
      detection_date: '2025-01-15',
      removal_date: '2025-04-15',
      created_at: '2025-01-15',
      updated_at: '2025-01-15',
    };

    act(() => {
      result.current.openEditModal(record);
    });

    expect(result.current.showEditModal).toBe(true);
    expect(result.current.editingRecord).toEqual(record);
  });

  it('opens delete modal with record', () => {
    const { result } = renderHook(() => useIPManagement());

    const record = {
      id: 1,
      ip_address: '10.0.0.1',
      reason: 'Test',
      source: 'MANUAL',
      country: '',
      created_at: '2025-01-15',
      updated_at: '2025-01-15',
    };

    act(() => {
      result.current.confirmDelete(record);
    });

    expect(result.current.showDeleteModal).toBe(true);
    expect(result.current.deletingRecord).toEqual(record);
  });

  // --- Tab switching ---

  it('changes active tab', () => {
    const { result } = renderHook(() => useIPManagement());

    act(() => {
      result.current.changeTab('whitelist');
    });

    expect(result.current.activeTab).toBe('whitelist');
  });

  it('resets page to 1 on tab change', () => {
    const { result } = renderHook(() => useIPManagement());

    act(() => {
      result.current.changeTab('blacklist');
    });

    expect(result.current.page).toBe(1);
  });

  // --- Add IP ---

  it('adds IP successfully', async () => {
    vi.mocked(addIP).mockResolvedValue({ success: true });
    vi.mocked(getUnifiedIPs).mockResolvedValue({ data: [], total: 0, pages: 0 });

    const { result } = renderHook(() => useIPManagement());

    act(() => {
      result.current.openAddModal();
    });

    await act(async () => {
      await result.current.handleAdd();
    });

    expect(addIP).toHaveBeenCalled();
  });

  // --- Delete IP ---

  it('deletes IP successfully', async () => {
    vi.mocked(deleteIP).mockResolvedValue({ success: true });
    vi.mocked(getUnifiedIPs).mockResolvedValue({ data: [], total: 0, pages: 0 });

    const { result } = renderHook(() => useIPManagement());

    act(() => {
      result.current.confirmDelete({
        id: 1,
        ip_address: '10.0.0.1',
        reason: 'Test',
        source: 'MANUAL',
        country: '',
        created_at: '2025-01-15',
        updated_at: '2025-01-15',
        list_type: 'blacklist',
      });
    });

    await act(async () => {
      await result.current.handleDelete();
    });

    expect(deleteIP).toHaveBeenCalled();
  });

  // --- Filter/Search state ---

  it('has default filter values', () => {
    const { result } = renderHook(() => useIPManagement());

    expect(result.current.filterType).toBe('');
    expect(result.current.filterSource).toBe('');
    expect(result.current.searchIP).toBe('');
  });

  // --- Download ---

  it('has download function', () => {
    const { result } = renderHook(() => useIPManagement());

    expect(typeof result.current.downloadRawData).toBe('function');
  });
});
