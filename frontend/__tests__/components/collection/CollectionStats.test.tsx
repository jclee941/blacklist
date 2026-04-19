import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CollectionStats } from '@/app/collection/components/CollectionStats';
import type { CollectionStatus, BlacklistStats } from '@/app/collection/components/types';

vi.mock('lucide-react', () => ({
  Activity: (props: Record<string, unknown>) => <svg data-testid="icon-activity" {...props} />,
  Database: (props: Record<string, unknown>) => <svg data-testid="icon-database" {...props} />,
  Clock: (props: Record<string, unknown>) => <svg data-testid="icon-clock" {...props} />,
  TrendingUp: (props: Record<string, unknown>) => <svg data-testid="icon-trending" {...props} />,
}));

vi.mock('@/components/ui/Card', () => ({
  StatCard: ({
    title,
    value,
    loading,
  }: {
    title: string;
    value: string;
    loading: boolean;
    icon: React.ComponentType;
    trend?: { value: number; isPositive: boolean };
  }) => <div data-testid={`stat-${title}`}>{loading ? 'Loading...' : `${title}: ${value}`}</div>,
}));

describe('CollectionStats', () => {
  const collectionStatus: CollectionStatus = {
    is_running: true,
    collectors: {
      REGTECH: {
        enabled: true,
        error_count: 0,
        interval_seconds: 3600,
        last_run: '2025-01-15T10:00:00Z',
        next_run: '2025-01-15T11:00:00Z',
        run_count: 10,
      },
    },
  };

  const blacklistStats: BlacklistStats = {
    current_total_ips: 12345,
    current_active_ips: 10000,
    today_collected: 50,
    week_collected: 350,
    month_collected: 1500,
    sources: {},
  };

  const defaultProps = {
    collectionStatus,
    blacklistStats,
    loading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders 4 stat cards', () => {
    render(<CollectionStats {...defaultProps} />);
    expect(screen.getByTestId('stat-수집 상태')).toBeInTheDocument();
    expect(screen.getByTestId('stat-현재 등록 IP')).toBeInTheDocument();
    expect(screen.getByTestId('stat-활성 수집기')).toBeInTheDocument();
    expect(screen.getByTestId('stat-마지막 업데이트')).toBeInTheDocument();
  });

  it('shows 수집 중 when is_running is true', () => {
    render(<CollectionStats {...defaultProps} />);
    expect(screen.getByTestId('stat-수집 상태')).toHaveTextContent('수집 중');
  });

  it('shows 대기 중 when is_running is false', () => {
    const idleStatus = { ...collectionStatus, is_running: false };
    render(<CollectionStats {...defaultProps} collectionStatus={idleStatus} />);
    expect(screen.getByTestId('stat-수집 상태')).toHaveTextContent('대기 중');
  });

  it('displays current total IPs from blacklistStats', () => {
    render(<CollectionStats {...defaultProps} />);
    expect(screen.getByTestId('stat-현재 등록 IP')).toHaveTextContent('12,345');
  });

  it('displays 0 when blacklistStats is null', () => {
    render(<CollectionStats {...defaultProps} blacklistStats={null} />);
    expect(screen.getByTestId('stat-현재 등록 IP')).toHaveTextContent('0');
  });

  it('displays active/total collectors count', () => {
    render(<CollectionStats {...defaultProps} />);
    expect(screen.getByTestId('stat-활성 수집기')).toHaveTextContent('1/1');
  });

  it('displays 0/0 when collectionStatus is null', () => {
    render(<CollectionStats {...defaultProps} collectionStatus={null} />);
    expect(screen.getByTestId('stat-활성 수집기')).toHaveTextContent('0/0');
  });

  it('displays last update time from most recent collector', () => {
    render(<CollectionStats {...defaultProps} />);
    expect(screen.getByTestId('stat-마지막 업데이트')).not.toHaveTextContent('-');
  });

  it('displays - for last update when collectionStatus is null', () => {
    render(<CollectionStats {...defaultProps} collectionStatus={null} />);
    expect(screen.getByTestId('stat-마지막 업데이트')).toHaveTextContent('-');
  });

  it('displays - for last update when no collectors have run', () => {
    const noRunStatus: CollectionStatus = {
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
    };
    render(<CollectionStats {...defaultProps} collectionStatus={noRunStatus} />);
    expect(screen.getByTestId('stat-마지막 업데이트')).toHaveTextContent('-');
  });

  it('shows loading state on all cards when loading is true', () => {
    render(<CollectionStats {...defaultProps} loading={true} />);
    const loadingElements = screen.getAllByText('Loading...');
    expect(loadingElements).toHaveLength(4);
  });
});
