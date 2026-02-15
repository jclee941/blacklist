import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import DatabaseOverviewClient from '@/app/database/DatabaseOverviewClient';

// Mock dependencies
vi.mock('lucide-react', () => ({
  Database: () => <div data-testid="icon-database" />,
  Table2: () => <div data-testid="icon-table" />,
  RefreshCw: () => <div data-testid="icon-refresh" />,
}));

// Mock API
vi.mock('@/lib/api', () => ({
  getDatabaseTables: vi.fn(),
  getSystemStatus: vi.fn(),
}));

import { getDatabaseTables, getSystemStatus } from '@/lib/api';

describe('DatabaseOverviewClient', () => {
  const mockTablesData = {
    success: true,
    tables: {
      users: { columns: ['id', 'name'], record_count: 10 },
      logs: { columns: ['id', 'msg', 'ts'], record_count: 50 },
    },
  };

  const mockSystemStatus = {
    host: 'localhost',
    port: '5432',
    database: 'blacklist_db',
    status: 'connected',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getDatabaseTables).mockResolvedValue(mockTablesData);
    vi.mocked(getSystemStatus).mockResolvedValue(mockSystemStatus);
  });

  it('renders loading state initially', () => {
    render(<DatabaseOverviewClient />);
    expect(screen.getByText('데이터 로딩 중...')).toBeInTheDocument();
  });

  it('renders data after fetching', async () => {
    render(<DatabaseOverviewClient />);

    await waitFor(() => {
      expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument();
    });

    // Header info
    expect(screen.getByText('테이블 현황')).toBeInTheDocument();

    // DB Info card
    expect(screen.getByText('blacklist_db')).toBeInTheDocument();
    expect(screen.getByText('localhost:5432')).toBeInTheDocument();

    // Table list
    expect(screen.getByText('users')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument(); // row count
    expect(screen.getByText('logs')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
  });

  it('handles refresh button click', async () => {
    render(<DatabaseOverviewClient />);

    await waitFor(() => {
      expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument();
    });

    const refreshBtn = screen.getByText('새로고침');
    fireEvent.click(refreshBtn);

    expect(getDatabaseTables).toHaveBeenCalledTimes(2);
    expect(getSystemStatus).toHaveBeenCalledTimes(2);
  });

  it('handles error state', async () => {
    vi.mocked(getDatabaseTables).mockRejectedValue(new Error('DB Error'));
    render(<DatabaseOverviewClient />);

    await waitFor(() => {
      expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument();
    });

    expect(screen.getByText('테이블 현황을 불러오지 못했습니다.')).toBeInTheDocument();
  });

  it('handles missing table data gracefully', async () => {
    vi.mocked(getDatabaseTables).mockResolvedValue({ success: false });
    render(<DatabaseOverviewClient />);

    await waitFor(() => {
      expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument();
    });

    expect(screen.getByText('테이블 데이터가 올바르지 않습니다.')).toBeInTheDocument();
  });

  it('renders empty state when no tables', async () => {
    vi.mocked(getDatabaseTables).mockResolvedValue({ success: true, tables: {} });
    render(<DatabaseOverviewClient />);

    await waitFor(() => {
      expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument();
    });

    expect(screen.getByText('테이블 정보가 없습니다')).toBeInTheDocument();
  });
});
