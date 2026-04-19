import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import AnalyticsPage from '@/app/analytics/page';

vi.mock('lucide-react', () => ({
  BarChart3: (props: Record<string, unknown>) => <svg data-testid="icon-bar" {...props} />,
  Calendar: (props: Record<string, unknown>) => <svg data-testid="icon-calendar" {...props} />,
  TrendingUp: (props: Record<string, unknown>) => <svg data-testid="icon-trending" {...props} />,
  AlertTriangle: (props: Record<string, unknown>) => <svg data-testid="icon-alert" {...props} />,
  RefreshCw: (props: Record<string, unknown>) => <svg data-testid="icon-refresh" {...props} />,
  ChevronLeft: (props: Record<string, unknown>) => (
    <svg data-testid="icon-chevron-left" {...props} />
  ),
  ChevronRight: (props: Record<string, unknown>) => (
    <svg data-testid="icon-chevron-right" {...props} />
  ),
}));

const mockGetDailyDetectionStats = vi.fn();

vi.mock('@/lib/api', () => ({
  getDailyDetectionStats: (days: number) => mockGetDailyDetectionStats(days),
}));

const mockAnalyticsResponse = {
  success: true,
  data: {
    metadata: {
      analysis_period_days: 365,
      total_ips: 10000,
      total_days: 120,
      avg_per_day: 83,
      generated_at: '2025-01-15T10:00:00Z',
    },
    timeline: [
      {
        detection_day: '2025-01-15',
        ip_count: 150,
        source_count: 1,
        sources: 'REGTECH',
        first_collected: '2025-01-15T00:00:00Z',
        last_collected: '2025-01-15T23:59:00Z',
        is_suspicious: false,
      },
      {
        detection_day: '2025-01-14',
        ip_count: 500,
        source_count: 1,
        sources: 'REGTECH',
        first_collected: '2025-01-14T00:00:00Z',
        last_collected: '2025-01-14T23:59:00Z',
        is_suspicious: true,
      },
    ],
    source_statistics: [
      {
        source: 'REGTECH',
        total_ips: 8000,
        active_days: 100,
        first_detection: '2024-10-01',
        last_detection: '2025-01-15',
        avg_per_day: 80,
      },
    ],
  },
};

describe('AnalyticsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetDailyDetectionStats.mockResolvedValue(mockAnalyticsResponse);
  });

  it('renders page heading', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('\uc77c\ubcc4 \ud0d0\uc9c0 \ud1b5\uacc4')).toBeInTheDocument();
    });
  });

  it('renders page description', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(
        screen.getByText(
          '\ud0d0\uc9c0\uc77c \uae30\uc900 IP \uc218\uc9d1 \ud604\ud669 \ubd84\uc11d'
        )
      ).toBeInTheDocument();
    });
  });

  it('renders period selector', async () => {
    render(<AnalyticsPage />);
    expect(screen.getByDisplayValue('\ucd5c\uadfc 1\ub144')).toBeInTheDocument();
  });

  it('renders refresh button', async () => {
    render(<AnalyticsPage />);
    expect(screen.getByText('\uc0c8\ub85c\uace0\uce68')).toBeInTheDocument();
  });

  it('calls getDailyDetectionStats with default 365 days', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(mockGetDailyDetectionStats).toHaveBeenCalledWith(365);
    });
  });

  it('shows metadata stats after loading', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('10,000')).toBeInTheDocument();
      expect(screen.getByText('120\uc77c')).toBeInTheDocument();
      expect(screen.getByText('83')).toBeInTheDocument();
    });
  });

  it('renders timeline table with data', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('\uc77c\ubcc4 \uc218\uc9d1 \ud604\ud669')).toBeInTheDocument();
      expect(screen.getByText('2025-01-15')).toBeInTheDocument();
      expect(screen.getByText('150')).toBeInTheDocument();
    });
  });

  it('shows source statistics section', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('\uc18c\uc2a4\ubcc4 \ud1b5\uacc4')).toBeInTheDocument();
      const regtechElements = screen.getAllByText('REGTECH');
      expect(regtechElements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('handles API errors gracefully', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    mockGetDailyDetectionStats.mockRejectedValue(new Error('API Error'));
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByText('\uc77c\ubcc4 \ud0d0\uc9c0 \ud1b5\uacc4')).toBeInTheDocument();
    });
  });

  it('changes period when selector changes', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(mockGetDailyDetectionStats).toHaveBeenCalledWith(365);
    });
    fireEvent.change(screen.getByDisplayValue('\ucd5c\uadfc 1\ub144'), {
      target: { value: '30' },
    });
    await waitFor(() => {
      expect(mockGetDailyDetectionStats).toHaveBeenCalledWith(30);
    });
  });
});
