import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import IPManagementClient from '@/app/ip-management/IPManagementClient';

// Mock child components
vi.mock('@/app/ip-management/components', () => ({
  useIPManagement: vi.fn(),
  IPManagementTabs: ({
    activeTab,
    onTabChange,
  }: {
    activeTab: string;
    onTabChange: (tab: string) => void;
  }) => (
    <div data-testid="ip-tabs">
      <button onClick={() => onTabChange('blacklist')}>Blacklist Tab</button>
      <button onClick={() => onTabChange('whitelist')}>Whitelist Tab</button>
      <span>Current: {activeTab}</span>
    </div>
  ),
  IPManagementFilters: ({
    onSearch,
    onReset,
    onAdd,
  }: {
    onSearch: () => void;
    onReset: () => void;
    onAdd: () => void;
  }) => (
    <div data-testid="ip-filters">
      <button onClick={onSearch}>Search</button>
      <button onClick={onReset}>Reset</button>
      <button onClick={onAdd}>Add</button>
    </div>
  ),
  IPManagementTable: ({
    onEdit,
    onDelete,
  }: {
    onEdit: (item: { id: number }) => void;
    onDelete: (item: { id: number }) => void;
  }) => (
    <div data-testid="ip-table">
      <button onClick={() => onEdit({ id: 1 })}>Edit 1</button>
      <button onClick={() => onDelete({ id: 1 })}>Delete 1</button>
    </div>
  ),
  IPManagementFormModal: ({ isOpen }: { isOpen?: boolean }) =>
    isOpen ? <div data-testid="ip-form-modal" /> : null,
  DeleteConfirmModal: ({ isOpen, onConfirm }: { isOpen?: boolean; onConfirm: () => void }) =>
    isOpen ? (
      <div data-testid="delete-confirm-modal">
        <button onClick={onConfirm}>Confirm Delete</button>
      </div>
    ) : null,
}));

import { useIPManagement } from '@/app/ip-management/components';

describe('IPManagementClient', () => {
  const mockUseIPManagement = {
    activeTab: 'blacklist' as const,
    data: [],
    loading: false,
    page: 1,
    total: 0,
    totalPages: 1,
    showAddModal: false,
    showEditModal: false,
    showDeleteModal: false,
    editingRecord: null,
    deletingRecord: null,
    formData: {
      ip_address: '',
      reason: '',
      source: 'MANUAL',
      country: '',
      is_active: true,
      detection_date: '',
      removal_date: '',
    },
    isSubmitting: false,
    submitSuccess: false,
    submitError: null,
    filterType: 'all',
    filterSource: 'all',
    searchIP: '',
    isDownloading: false,
    setPage: vi.fn(),
    setFormData: vi.fn(),
    setFilterType: vi.fn(),
    setFilterSource: vi.fn(),
    setSearchIP: vi.fn(),
    changeTab: vi.fn(),
    fetchData: vi.fn(),
    handleAdd: vi.fn(),
    handleEdit: vi.fn(),
    handleDelete: vi.fn(),
    openEditModal: vi.fn(),
    confirmDelete: vi.fn(),
    downloadRawData: vi.fn(),
    openAddModal: vi.fn(),
    closeAddModal: vi.fn(),
    closeEditModal: vi.fn(),
    closeDeleteModal: vi.fn(),
  };

  beforeEach(() => {
    vi.mocked(useIPManagement).mockReturnValue(mockUseIPManagement);
  });

  it('renders correctly', () => {
    render(<IPManagementClient />);
    expect(screen.getByTestId('ip-tabs')).toBeInTheDocument();
    expect(screen.getByTestId('ip-filters')).toBeInTheDocument();
    expect(screen.getByTestId('ip-table')).toBeInTheDocument();
  });

  it('displays success message when submitSuccess is true', () => {
    vi.mocked(useIPManagement).mockReturnValue({
      ...mockUseIPManagement,
      submitSuccess: true,
    });
    render(<IPManagementClient />);
    expect(screen.getByText(/항목이 성공적으로 추가\/수정되었습니다/)).toBeInTheDocument();
  });

  it('displays error message when submitError is present', () => {
    vi.mocked(useIPManagement).mockReturnValue({
      ...mockUseIPManagement,
      submitError: 'Something went wrong',
    });
    render(<IPManagementClient />);
    expect(screen.getByText('오류: Something went wrong')).toBeInTheDocument();
  });

  it('handles tab change interaction', () => {
    const changeTabMock = vi.fn();
    vi.mocked(useIPManagement).mockReturnValue({
      ...mockUseIPManagement,
      changeTab: changeTabMock,
    });
    render(<IPManagementClient />);

    fireEvent.click(screen.getByText('Whitelist Tab'));
    expect(changeTabMock).toHaveBeenCalledWith('whitelist');
  });

  it('handles add button click', () => {
    const openAddModalMock = vi.fn();
    vi.mocked(useIPManagement).mockReturnValue({
      ...mockUseIPManagement,
      openAddModal: openAddModalMock,
    });
    render(<IPManagementClient />);

    fireEvent.click(screen.getByText('Add'));
    expect(openAddModalMock).toHaveBeenCalled();
  });

  it('resets search state without scheduling an uncancelled delayed refresh', () => {
    const setSearchIPMock = vi.fn();
    const setPageMock = vi.fn();
    const fetchDataMock = vi.fn();

    vi.mocked(useIPManagement).mockReturnValue({
      ...mockUseIPManagement,
      setSearchIP: setSearchIPMock,
      setPage: setPageMock,
      fetchData: fetchDataMock,
    });

    const setTimeoutSpy = vi.spyOn(global, 'setTimeout');
    render(<IPManagementClient />);

    fireEvent.click(screen.getByText('Reset'));

    expect(setSearchIPMock).toHaveBeenCalledWith('');
    expect(setPageMock).toHaveBeenCalledWith(1);
    expect(setTimeoutSpy).not.toHaveBeenCalled();
    setTimeoutSpy.mockRestore();
  });

  it('shows modals when flags are true', () => {
    vi.mocked(useIPManagement).mockReturnValue({
      ...mockUseIPManagement,
      showAddModal: true,
      showDeleteModal: true,
    });
    render(<IPManagementClient />);

    expect(screen.getByTestId('ip-form-modal')).toBeInTheDocument();
    expect(screen.getByTestId('delete-confirm-modal')).toBeInTheDocument();
  });

  it('handles delete confirmation', () => {
    const handleDeleteMock = vi.fn();
    vi.mocked(useIPManagement).mockReturnValue({
      ...mockUseIPManagement,
      showDeleteModal: true,
      handleDelete: handleDeleteMock,
    });
    render(<IPManagementClient />);

    fireEvent.click(screen.getByText('Confirm Delete'));
    expect(handleDeleteMock).toHaveBeenCalled();
  });
});
