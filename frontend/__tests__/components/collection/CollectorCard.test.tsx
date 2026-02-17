import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CollectorCard } from '@/app/collection/components/CollectorCard';
import type { Credential, CollectorStatus } from '@/app/collection/components/types';

vi.mock('lucide-react', () => ({
  Settings: (props: Record<string, unknown>) => <svg data-testid="icon-settings" {...props} />,
  Play: (props: Record<string, unknown>) => <svg data-testid="icon-play" {...props} />,
  RefreshCw: (props: Record<string, unknown>) => <svg data-testid="icon-refresh" {...props} />,
  CheckCircle: (props: Record<string, unknown>) => <svg data-testid="icon-check" {...props} />,
  XCircle: (props: Record<string, unknown>) => <svg data-testid="icon-xcircle" {...props} />,
  AlertCircle: (props: Record<string, unknown>) => <svg data-testid="icon-alert" {...props} />,
  Lock: (props: Record<string, unknown>) => <svg data-testid="icon-lock" {...props} />,
  Clock: (props: Record<string, unknown>) => <svg data-testid="icon-clock" {...props} />,
}));

vi.mock('@/components/ui/Button', () => ({
  default: ({
    children,
    onClick,
    loading,
    disabled,
    variant,
    size,
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    loading?: boolean;
    disabled?: boolean;
    variant?: string;
    size?: string;
  }) => (
    <button
      onClick={onClick}
      disabled={!!disabled || !!loading}
      data-variant={variant}
      data-size={size}
      type="button"
    >
      {loading ? 'Loading...' : children}
    </button>
  ),
}));

vi.mock('@/components/ui/Card', () => ({
  Card: ({ children, padding }: { children: React.ReactNode; padding?: string }) => (
    <div data-testid="card" data-padding={padding}>
      {children}
    </div>
  ),
}));

describe('CollectorCard', () => {
  const defaultCredential: Credential = {
    service_name: 'REGTECH',
    username: 'testuser',
    enabled: true,
    collection_interval: '3600',
    last_collection: '2025-01-15T10:00:00Z',
    connection_status: 'connected',
  };

  const defaultCollectorStatus: CollectorStatus = {
    enabled: true,
    error_count: 0,
    interval_seconds: 3600,
    last_run: '2025-01-15T10:00:00Z',
    next_run: '2025-01-15T11:00:00Z',
    run_count: 42,
  };

  const defaultProps = {
    credential: defaultCredential,
    collectorStatus: defaultCollectorStatus,
    testingConnection: false,
    triggeringCollection: false,
    onTest: vi.fn(),
    onTrigger: vi.fn(),
    onEdit: vi.fn(),
    getSourceCount: vi.fn().mockReturnValue(1500),
    formatInterval: vi.fn().mockReturnValue('1시간'),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    defaultProps.getSourceCount.mockReturnValue(1500);
    defaultProps.formatInterval.mockReturnValue('1시간');
  });

  it('renders service name and username', () => {
    render(<CollectorCard {...defaultProps} />);
    expect(screen.getByText('REGTECH')).toBeInTheDocument();
    expect(screen.getByText('testuser')).toBeInTheDocument();
  });

  it('renders inside a Card component', () => {
    render(<CollectorCard {...defaultProps} />);
    expect(screen.getByTestId('card')).toBeInTheDocument();
  });

  it('displays IP count from getSourceCount', () => {
    render(<CollectorCard {...defaultProps} />);
    expect(defaultProps.getSourceCount).toHaveBeenCalledWith('REGTECH');
    expect(screen.getByText('1,500')).toBeInTheDocument();
  });

  it('displays formatted interval', () => {
    render(<CollectorCard {...defaultProps} />);
    expect(screen.getByText('1시간')).toBeInTheDocument();
  });

  it('displays last collection time', () => {
    render(<CollectorCard {...defaultProps} />);
    expect(screen.getByText(/마지막 수집:.*2025-01-15T10:00:00Z/)).toBeInTheDocument();
  });

  it('shows 없음 when no last collection', () => {
    const noLastRun = { ...defaultCredential, last_collection: undefined };
    const noLastRunStatus = { ...defaultCollectorStatus, last_run: null };
    render(
      <CollectorCard {...defaultProps} credential={noLastRun} collectorStatus={noLastRunStatus} />
    );
    expect(screen.getByText(/마지막 수집:.*없음/)).toBeInTheDocument();
  });

  it('shows 활성화 when both credential and collector are enabled', () => {
    render(<CollectorCard {...defaultProps} />);
    expect(screen.getByText(/상태:.*활성화/)).toBeInTheDocument();
  });

  it('shows 비활성화 when credential is disabled', () => {
    const disabledCred = { ...defaultCredential, enabled: false };
    render(<CollectorCard {...defaultProps} credential={disabledCred} />);
    expect(screen.getByText(/상태:.*비활성화/)).toBeInTheDocument();
  });

  it('shows 비활성화 when collector status is disabled', () => {
    const disabledStatus = { ...defaultCollectorStatus, enabled: false };
    render(<CollectorCard {...defaultProps} collectorStatus={disabledStatus} />);
    expect(screen.getByText(/상태:.*비활성화/)).toBeInTheDocument();
  });

  it('shows status_message when present', () => {
    const withMessage = { ...defaultCredential, status_message: '연결 오류 발생' };
    render(<CollectorCard {...defaultProps} credential={withMessage} />);
    expect(screen.getByText('연결 오류 발생')).toBeInTheDocument();
  });

  it('does not show status_message when absent', () => {
    render(<CollectorCard {...defaultProps} />);
    expect(screen.queryByText('연결 오류 발생')).not.toBeInTheDocument();
  });

  describe('connection status badges', () => {
    it('shows 연결됨 badge for connected status', () => {
      render(<CollectorCard {...defaultProps} />);
      expect(screen.getByText('연결됨')).toBeInTheDocument();
    });

    it('shows 미확인 badge for failed status (falls to default)', () => {
      const failedCred = { ...defaultCredential, connection_status: 'failed' as const };
      render(<CollectorCard {...defaultProps} credential={failedCred} />);
      expect(screen.getByText('미확인')).toBeInTheDocument();
    });

    it('shows 미확인 badge for unknown status', () => {
      const unknownCred = { ...defaultCredential, connection_status: 'unknown' as const };
      render(<CollectorCard {...defaultProps} credential={unknownCred} />);
      expect(screen.getByText('미확인')).toBeInTheDocument();
    });

    it('shows 미확인 badge when status is undefined', () => {
      const noCred = { ...defaultCredential, connection_status: undefined };
      render(<CollectorCard {...defaultProps} credential={noCred} />);
      expect(screen.getByText('미확인')).toBeInTheDocument();
    });
  });

  describe('action buttons', () => {
    it('calls onTest with service name when test button is clicked', () => {
      render(<CollectorCard {...defaultProps} />);
      fireEvent.click(screen.getByText('테스트'));
      expect(defaultProps.onTest).toHaveBeenCalledWith('REGTECH');
    });

    it('calls onTrigger with service name when collect button is clicked', () => {
      render(<CollectorCard {...defaultProps} />);
      fireEvent.click(screen.getByText('수집'));
      expect(defaultProps.onTrigger).toHaveBeenCalledWith('REGTECH');
    });

    it('calls onEdit with service name when settings button is clicked', () => {
      render(<CollectorCard {...defaultProps} />);
      fireEvent.click(screen.getByText('설정'));
      expect(defaultProps.onEdit).toHaveBeenCalledWith('REGTECH');
    });

    it('shows loading state on test button when testingConnection', () => {
      render(<CollectorCard {...defaultProps} testingConnection={true} />);
      const loadingButtons = screen.getAllByText('Loading...');
      expect(loadingButtons.length).toBeGreaterThan(0);
    });

    it('disables collect button when not enabled', () => {
      const disabledCred = { ...defaultCredential, enabled: false };
      render(<CollectorCard {...defaultProps} credential={disabledCred} />);
      expect(screen.getByText('수집')).toBeDisabled();
    });
  });
});
