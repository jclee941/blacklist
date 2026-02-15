import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import FortinetClient from '@/app/fortinet/FortinetClient';

// Mock dependencies
vi.mock('lucide-react', () => ({
  Download: () => <div data-testid="icon-download" />,
  RefreshCw: () => <div data-testid="icon-refresh" />,
  AlertCircle: () => <div data-testid="icon-alert" />,
  CheckCircle: () => <div data-testid="icon-check" />,
  Activity: () => <div data-testid="icon-activity" />,
}));

// Mock API
vi.mock('@/lib/api', () => ({
  getFortinetPullLogs: vi.fn(),
  getFortinetBlocklist: vi.fn(),
}));

import { getFortinetPullLogs, getFortinetBlocklist } from '@/lib/api';

describe('FortinetClient', () => {
  const mockPullLogsData = {
    success: true,
    data: [
      {
        id: 1,
        device_ip: '192.168.1.1',
        endpoint: '/api/v1/list',
        ip_count: 500,
        response_time_ms: 100,
        status_code: 200,
        created_at: '2023-01-01T12:00:00Z',
        user_agent: 'FortiGate/7.0',
      },
      {
        id: 2,
        device_ip: '192.168.1.2',
        endpoint: '/api/v1/list',
        ip_count: 0,
        response_time_ms: 50,
        status_code: 500,
        created_at: '2023-01-01T13:00:00Z',
        user_agent: 'FortiGate/7.0',
      },
    ],
    stats: {
      total_pulls: 10,
      successful_pulls: 9,
      failed_pulls: 1,
      unique_devices: 2,
    },
  };

  const mockBlocklistResponse = {
    data: {
      success: true,
      data: {
        blocklist: '1.1.1.1\n2.2.2.2',
      },
    },
    headers: {} as Record<string, string>,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getFortinetPullLogs).mockResolvedValue(mockPullLogsData);
    vi.mocked(getFortinetBlocklist).mockResolvedValue(mockBlocklistResponse);

    // Mock URL.createObjectURL and revokeObjectURL for download test
    global.URL.createObjectURL = vi.fn(() => 'blob:test');
    global.URL.revokeObjectURL = vi.fn();

    // Mock window.location for External Connector URL test
    Object.defineProperty(window, 'location', {
      value: { origin: 'http://localhost:3000' },
      writable: true,
    });
  });

  it('renders loading state initially', () => {
    render(<FortinetClient />);
    expect(screen.getByText('데이터 로딩 중...')).toBeInTheDocument();
  });

  it('renders data after fetching', async () => {
    render(<FortinetClient />);

    await waitFor(
      () => {
        expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    // Stats
    expect(screen.getByText('전체 요청')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument(); // total_pulls
    expect(screen.getByText('9')).toBeInTheDocument(); // successful
    expect(screen.getByText('1')).toBeInTheDocument(); // failed

    // Log Table
    expect(screen.getByText('192.168.1.1')).toBeInTheDocument();
    expect(screen.getByText('500')).toBeInTheDocument(); // ip_count
    expect(screen.getAllByText('성공')[0]).toBeInTheDocument();
    expect(screen.getByText('192.168.1.2')).toBeInTheDocument();
    expect(screen.getAllByText('실패')[0]).toBeInTheDocument();
  });

  it('handles refresh button click', async () => {
    render(<FortinetClient />);
    await waitFor(() => expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument());

    const refreshBtn = screen.getByText('새로고침');
    fireEvent.click(refreshBtn);

    expect(getFortinetPullLogs).toHaveBeenCalledTimes(2);
  });

  it('handles download blocklist', async () => {
    render(<FortinetClient />);
    await waitFor(() => expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument());

    const downloadBtn = screen.getByText('블랙리스트 다운로드');
    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(getFortinetBlocklist).toHaveBeenCalled();
      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });
  });

  it('handles error state', async () => {
    vi.mocked(getFortinetPullLogs).mockRejectedValue(new Error('Fetch Error'));
    render(<FortinetClient />);

    await waitFor(() => {
      expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument();
    });

    expect(screen.getByText('Fetch Error')).toBeInTheDocument();
  });

  it('displays correct external connector URL', async () => {
    render(<FortinetClient />);
    await waitFor(() => expect(screen.queryByText('데이터 로딩 중...')).not.toBeInTheDocument());

    expect(
      screen.getByText(/http:\/\/localhost:3000\/api\/fortinet\/blocklist/)
    ).toBeInTheDocument();
  });
});
