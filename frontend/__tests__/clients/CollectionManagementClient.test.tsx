import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CollectionManagementClient from '@/app/collection/CollectionManagementClient';

// Mock dependencies
vi.mock('lucide-react', () => ({
  RefreshCw: () => <div data-testid="icon-refresh" />,
  AlertCircle: () => <div data-testid="icon-alert" />,
  CheckCircle: () => <div data-testid="icon-check" />,
}));

vi.mock('@/components/ui/Button', () => ({
  default: ({
    children,
    onClick,
    disabled,
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
  }) => (
    <button type="button" onClick={onClick} disabled={disabled} data-testid="ui-button">
      {children}
    </button>
  ),
}));

vi.mock('@/components/ui/LoadingSpinner', () => ({
  default: ({ message }: { message?: string }) => (
    <div data-testid="loading-spinner">{message}</div>
  ),
}));

vi.mock('@/components/ui/PageHeader', () => ({
  default: ({ title }: { title?: string }) => <h1 data-testid="page-header">{title}</h1>,
}));

// Mock child components to isolate the client test
vi.mock('@/app/collection/components', () => ({
  CollectionStats: () => <div data-testid="collection-stats" />,
  CollectorCard: ({ credential }: { credential: { service_name: string } }) => (
    <div data-testid={`collector-card-${credential.service_name}`} />
  ),
  CredentialEditModal: ({ show, loading }: { show?: boolean; loading?: boolean }) =>
    show ? <div data-testid="credential-modal" data-loading={String(loading)} /> : null,
  useCollectionManagement: vi.fn(),
}));

import { useCollectionManagement } from '@/app/collection/components';

describe('CollectionManagementClient', () => {
  const mockUseCollectionManagement: ReturnType<typeof useCollectionManagement> = {
    credentials: [],
    collectionStatus: null,
    blacklistStats: null,
    loading: true,
    testingConnection: {},
    triggeringCollection: {},
    showCredentialModal: false,
    editingService: null,
    notification: null,
    credentialForm: { username: '', password: '', enabled: true, collection_interval: 'daily' },
    fetchData: vi.fn(),
    saveCredentials: vi.fn(),
    testConnection: vi.fn(),
    triggerCollection: vi.fn(),
    openEditModal: vi.fn(),
    closeEditModal: vi.fn(),
    setCredentialForm: vi.fn(),
    getSourceCount: vi.fn(),
    formatInterval: vi.fn(),
    saving: false,
    clearNotification: vi.fn(),
  };

  beforeEach(() => {
    vi.mocked(useCollectionManagement).mockReturnValue(mockUseCollectionManagement);
  });

  it('renders loading state initially', () => {
    vi.mocked(useCollectionManagement).mockReturnValue({
      ...mockUseCollectionManagement,
      loading: true,
    });
    render(<CollectionManagementClient />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('renders content when loading is complete', () => {
    vi.mocked(useCollectionManagement).mockReturnValue({
      ...mockUseCollectionManagement,
      loading: false,
      credentials: [
        {
          service_name: 'REGTECH',
          configured: true,
          username: 'user',
          enabled: true,
          collection_interval: 'daily',
        },
      ],
    });
    render(<CollectionManagementClient />);
    expect(screen.getByTestId('page-header')).toHaveTextContent('수집 관리');
    expect(screen.getByTestId('collection-stats')).toBeInTheDocument();
    expect(screen.getByTestId('collector-card-REGTECH')).toBeInTheDocument();
  });

  it('shows notification when present', () => {
    vi.mocked(useCollectionManagement).mockReturnValue({
      ...mockUseCollectionManagement,
      loading: false,
      notification: { type: 'success', message: 'Operation successful' },
    });
    render(<CollectionManagementClient />);
    expect(screen.getByText('Operation successful')).toBeInTheDocument();
    expect(screen.getByTestId('icon-check')).toBeInTheDocument();
  });

  it('handles refresh button click', () => {
    const fetchDataMock = vi.fn();
    vi.mocked(useCollectionManagement).mockReturnValue({
      ...mockUseCollectionManagement,
      loading: false,
      fetchData: fetchDataMock,
    });
    render(<CollectionManagementClient />);

    const refreshBtn = screen.getByText('새로고침');
    fireEvent.click(refreshBtn);
    expect(fetchDataMock).toHaveBeenCalled();
  });

  it('shows credential modal when active', () => {
    vi.mocked(useCollectionManagement).mockReturnValue({
      ...mockUseCollectionManagement,
      loading: false,
      showCredentialModal: true,
    });
    render(<CollectionManagementClient />);
    expect(screen.getByTestId('credential-modal')).toBeInTheDocument();
  });

  it('passes the dedicated saving state to the credential modal', () => {
    vi.mocked(useCollectionManagement).mockReturnValue({
      ...mockUseCollectionManagement,
      loading: false,
      saving: true,
      showCredentialModal: true,
    });
    render(<CollectionManagementClient />);
    expect(screen.getByTestId('credential-modal')).toHaveAttribute('data-loading', 'true');
  });
});
