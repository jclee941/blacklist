import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import Dashboard from '@/app/page';

vi.mock('lucide-react', () => ({
  Database: (props: Record<string, unknown>) => <svg data-testid="icon-database" {...props} />,
  Shield: (props: Record<string, unknown>) => <svg data-testid="icon-shield" {...props} />,
  PlusCircle: (props: Record<string, unknown>) => <svg data-testid="icon-plus" {...props} />,
  Clock: (props: Record<string, unknown>) => <svg data-testid="icon-clock" {...props} />,
  Activity: (props: Record<string, unknown>) => <svg data-testid="icon-activity" {...props} />,
  TrendingUp: (props: Record<string, unknown>) => <svg data-testid="icon-trending" {...props} />,
  Globe: (props: Record<string, unknown>) => <svg data-testid="icon-globe" {...props} />,
  History: (props: Record<string, unknown>) => <svg data-testid="icon-history" {...props} />,
  Table2: (props: Record<string, unknown>) => <svg data-testid="icon-table" {...props} />,
  CheckCircle: (props: Record<string, unknown>) => <svg data-testid="icon-check" {...props} />,
  AlertTriangle: (props: Record<string, unknown>) => <svg data-testid="icon-alert" {...props} />,
  Loader2: (props: Record<string, unknown>) => <svg data-testid="icon-loader" {...props} />,
  BarChart3: (props: Record<string, unknown>) => <svg data-testid="icon-bar" {...props} />,
}));

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockGetStats = vi.fn();
const mockGetSystemStatus = vi.fn();
const mockGetCollectionHistory = vi.fn();
const mockGetCollectionStatus = vi.fn();
const mockGetWhitelist = vi.fn();

vi.mock('@/lib/api', () => ({
  getStats: () => mockGetStats(),
  getSystemStatus: () => mockGetSystemStatus(),
  getCollectionHistory: () => mockGetCollectionHistory(),
  getCollectionStatus: () => mockGetCollectionStatus(),
  getWhitelist: () => mockGetWhitelist(),
}));

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });

    mockGetStats.mockResolvedValue({
      stats: {
        total_ips: 5000,
        active_ips: 3000,
        recent_additions: 50,
        last_update: '2025-01-15T10:00:00Z',
      },
    });
    mockGetWhitelist.mockResolvedValue({
      data: { pagination: { total: 200 } },
    });
    mockGetSystemStatus.mockResolvedValue({
      status: 'healthy',
      service: { status: 'healthy' },
      components: { database: { status: 'healthy' } },
      collection: { collection_enabled: true },
    });
    mockGetCollectionHistory.mockResolvedValue({
      data: [
        {
          service_name: 'REGTECH',
          items_collected: 100,
          success: true,
          collection_date: '2025-01-15T10:00:00Z',
        },
      ],
    });
    mockGetCollectionStatus.mockResolvedValue({
      success: true,
      data: {
        is_running: false,
        collectors: {
          REGTECH: {
            enabled: true,
            error_count: 0,
            interval_seconds: 3600,
            last_run: null,
            next_run: null,
            run_count: 0,
          },
        },
      },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders dashboard heading', async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('\ub300\uc2dc\ubcf4\ub4dc')).toBeInTheDocument();
    });
  });

  it('renders dashboard description', async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(
        screen.getByText(
          '\uc2e4\uc2dc\uac04 IP \ube14\ub799\ub9ac\uc2a4\ud2b8 \ubaa8\ub2c8\ud130\ub9c1 \ubc0f \uad00\ub9ac'
        )
      ).toBeInTheDocument();
    });
  });

  it('shows stat cards after loading', async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('5,000')).toBeInTheDocument();
      expect(screen.getByText('3,000')).toBeInTheDocument();
      expect(screen.getByText('50')).toBeInTheDocument();
      expect(screen.getByText('200')).toBeInTheDocument();
    });
  });

  it('renders stat card titles', async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('\uc804\uccb4 IP \uc8fc\uc18c')).toBeInTheDocument();
      expect(screen.getByText('\ucc28\ub2e8\ub41c IP')).toBeInTheDocument();
      expect(screen.getByText('24\uc2dc\uac04 \uc2e0\uaddc')).toBeInTheDocument();
      expect(screen.getByText('\ud654\uc774\ud2b8\ub9ac\uc2a4\ud2b8')).toBeInTheDocument();
    });
  });

  it('renders quick action links', async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('IP \uad00\ub9ac')).toBeInTheDocument();
      expect(screen.getByText('\ub370\uc774\ud130 \uc218\uc9d1')).toBeInTheDocument();
      expect(screen.getByText('\uc77c\ubcc4 \ud1b5\uacc4')).toBeInTheDocument();
      expect(screen.getByText('FortiGate \uc5f0\ub3d9')).toBeInTheDocument();
    });
  });

  it('renders system status section after loading', async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('\uc2dc\uc2a4\ud15c \uc0c1\ud0dc')).toBeInTheDocument();
      expect(screen.getByText('API \uc11c\ubc84')).toBeInTheDocument();
    });
  });

  it('shows healthy system status', async () => {
    render(<Dashboard />);
    await waitFor(() => {
      const statusTexts = screen.getAllByText('\uc815\uc0c1');
      expect(statusTexts.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('renders recent activity section', async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('\ucd5c\uadfc \uc218\uc9d1 \ud65c\ub3d9')).toBeInTheDocument();
    });
  });

  it('shows recent activity entries', async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('REGTECH')).toBeInTheDocument();
      expect(screen.getByText(/100\uac1c \uc218\uc9d1/)).toBeInTheDocument();
    });
  });

  it('shows empty activity message when no activities', async () => {
    mockGetCollectionHistory.mockResolvedValue({ data: [] });
    render(<Dashboard />);
    await waitFor(() => {
      expect(
        screen.getByText('\ucd5c\uadfc \uc218\uc9d1 \ud65c\ub3d9\uc774 \uc5c6\uc2b5\ub2c8\ub2e4')
      ).toBeInTheDocument();
    });
  });

  it('calls all API functions on mount', async () => {
    render(<Dashboard />);
    await waitFor(() => {
      expect(mockGetStats).toHaveBeenCalled();
      expect(mockGetSystemStatus).toHaveBeenCalled();
      expect(mockGetCollectionHistory).toHaveBeenCalled();
      expect(mockGetCollectionStatus).toHaveBeenCalled();
      expect(mockGetWhitelist).toHaveBeenCalled();
    });
  });

  it('does not start a second collection status request while the first poll is pending', async () => {
    mockGetCollectionStatus.mockReturnValue(new Promise(() => {}));
    render(<Dashboard />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(mockGetCollectionStatus).toHaveBeenCalledTimes(1);
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(mockGetCollectionStatus).toHaveBeenCalledTimes(1);
  });

  it('handles API errors gracefully', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    mockGetStats.mockRejectedValue(new Error('Network error'));
    mockGetWhitelist.mockRejectedValue(new Error('Network error'));
    render(<Dashboard />);
    await waitFor(() => {
      expect(screen.getByText('\ub300\uc2dc\ubcf4\ub4dc')).toBeInTheDocument();
    });
  });

  it('shows collection running banner when is_running is true', async () => {
    mockGetCollectionStatus.mockResolvedValue({
      success: true,
      data: {
        is_running: true,
        collectors: {
          REGTECH: {
            enabled: true,
            error_count: 0,
            interval_seconds: 3600,
            last_run: null,
            next_run: null,
            run_count: 0,
          },
        },
      },
    });
    render(<Dashboard />);
    await waitFor(() => {
      expect(
        screen.getByText('\ub370\uc774\ud130 \uc218\uc9d1 \uc9c4\ud589 \uc911')
      ).toBeInTheDocument();
    });
  });
});
