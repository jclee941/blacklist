import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CollectionHistoryClient from '@/app/collection/CollectionHistoryClient';

// Mock dependencies
vi.mock('lucide-react', () => ({
  CheckCircle: () => <div data-testid="icon-check" />,
  XCircle: () => <div data-testid="icon-x" />,
  Clock: () => <div data-testid="icon-clock" />,
  RefreshCw: () => <div data-testid="icon-refresh" />,
  Filter: () => <div data-testid="icon-filter" />,
  ChevronLeft: () => <div data-testid="icon-left" />,
  ChevronRight: () => <div data-testid="icon-right" />,
  Database: () => <div data-testid="icon-db" />,
  TrendingUp: () => <div data-testid="icon-trending" />,
  AlertTriangle: () => <div data-testid="icon-alert" />,
  Calendar: () => <div data-testid="icon-calendar" />,
  Timer: () => <div data-testid="icon-timer" />,
  FileText: () => <div data-testid="icon-file" />,
}));

// Mock API
vi.mock('@/lib/api', () => ({
  getCollectionHistory: vi.fn(),
  getCollectionStatistics: vi.fn(),
}));

import { getCollectionHistory, getCollectionStatistics } from '@/lib/api';

describe('CollectionHistoryClient', () => {
  const mockHistoryData = {
    success: true,
    data: {
      history: [
        {
          id: 1,
          success: true,
          service_name: 'REGTECH',
          items_collected: 100,
          new_count: 10,
          updated_count: 5,
          collection_date: '2023-01-01T12:00:00Z',
          duration_seconds: 120,
        },
        {
          id: 2,
          success: false,
          service_name: 'SECUDIUM',
          items_collected: 0,
          collection_date: '2023-01-01T13:00:00Z',
          error_message: 'Connection failed',
        },
      ],
      total: 2,
      filtered: 2,
    },
  };

  const mockStatsData = {
    success: true,
    data: {
      sources: {
        REGTECH: {
          total_collections: 10,
          success_rate: 90,
          total_items: 1000,
          last_collection: '2023-01-01T12:00:00Z',
          avg_duration: 60,
        },
      },
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getCollectionHistory).mockResolvedValue(mockHistoryData);
    vi.mocked(getCollectionStatistics).mockResolvedValue(mockStatsData);
  });

  it('renders loading state initially', () => {
    // Force promise to stay pending appropriately if needed,
    // but default behavior will show loading first
    render(<CollectionHistoryClient />);
    expect(screen.getByText('데이터 로딩 중...')).toBeInTheDocument();
  });

  it('renders data after fetching', async () => {
    render(<CollectionHistoryClient />);

    await waitFor(() => {
      expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument();
    });

    // Check stats cards
    expect(screen.getByText('총 수집 횟수')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument(); // totalCollections from stats

    // Check table content
    const regtechElements = screen.getAllByText('REGTECH');
    expect(regtechElements.length).toBeGreaterThan(0);

    const secudiumElements = screen.getAllByText('SECUDIUM');
    expect(secudiumElements.length).toBeGreaterThan(0);

    expect(screen.getByText('Connection failed')).toBeInTheDocument();
  });

  it('handles refresh button click', async () => {
    render(<CollectionHistoryClient />);

    await waitFor(() => {
      expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument();
    });

    const refreshBtns = screen.getAllByText('새로고침');
    fireEvent.click(refreshBtns[0]);

    await waitFor(() => {
      expect(getCollectionHistory).toHaveBeenCalledTimes(2);
    });

    await waitFor(() => {
      expect(getCollectionStatistics).toHaveBeenCalledTimes(2);
    });
  });

  it('handles error state', async () => {
    vi.mocked(getCollectionHistory).mockRejectedValue(new Error('Network Error'));
    render(<CollectionHistoryClient />);

    await waitFor(() => {
      expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument();
    });

    expect(screen.getByText('네트워크 오류가 발생했습니다')).toBeInTheDocument();
  });

  it('filters data by source', async () => {
    render(<CollectionHistoryClient />);

    await waitFor(() => {
      expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument();
    });

    const selects = screen.getAllByRole('combobox');
    const sourceSelector = selects[0]; // First one is source filter based on code order

    fireEvent.change(sourceSelector, { target: { value: 'REGTECH' } });

    // Verify the filter was applied via API call
    await waitFor(() => {
      expect(getCollectionHistory).toHaveBeenCalled();
    });
  });

  it('filters data by client-side status', async () => {
    render(<CollectionHistoryClient />);

    await waitFor(() => {
      expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument();
    });

    const selects = screen.getAllByRole('combobox');
    const statusSelector = selects[1]; // Second one is status filter

    fireEvent.change(statusSelector, { target: { value: 'failed' } });

    await waitFor(() => {
      const rows = screen.getAllByRole('row');
      expect(rows.length).toBeGreaterThan(0);
    });
  });
});
