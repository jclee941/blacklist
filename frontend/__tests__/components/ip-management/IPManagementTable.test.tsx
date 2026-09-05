import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { IPManagementTable } from '@/app/ip-management/components/IPManagementTable';
import type { IPRecord, TabType } from '@/app/ip-management/components/types';

vi.mock('lucide-react', () => ({
  Edit2: (props: Record<string, unknown>) => <svg data-testid="icon-edit" {...props} />,
  Trash2: (props: Record<string, unknown>) => <svg data-testid="icon-trash" {...props} />,
  CheckCircle: (props: Record<string, unknown>) => <svg data-testid="icon-check" {...props} />,
  XCircle: (props: Record<string, unknown>) => <svg data-testid="icon-xcircle" {...props} />,
  AlertTriangle: (props: Record<string, unknown>) => <svg data-testid="icon-alert" {...props} />,
}));

const makeRecord = (overrides: Partial<IPRecord> = {}): IPRecord => ({
  id: 1,
  ip_address: '192.168.1.1',
  reason: 'Malicious',
  source: 'MANUAL',
  country: 'KR',
  is_active: true,
  auto_active: true,
  detection_date: '2025-01-01',
  removal_date: '2025-04-01',
  detection_count: 3,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  list_type: 'blacklist',
  ...overrides,
});

const defaultProps = {
  activeTab: 'blacklist' as TabType,
  data: [makeRecord()],
  loading: false,
  page: 1,
  total: 1,
  totalPages: 1,
  onPageChange: vi.fn(),
  onEdit: vi.fn(),
  onDelete: vi.fn(),
};

describe('IPManagementTable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('loading state', () => {
    it('shows loading message', () => {
      render(<IPManagementTable {...defaultProps} loading={true} />);
      expect(screen.getByText('로딩 중...')).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('shows empty message when no data', () => {
      render(<IPManagementTable {...defaultProps} data={[]} />);
      expect(screen.getByText('데이터가 없습니다')).toBeInTheDocument();
    });
  });

  describe('data rendering', () => {
    it('renders IP address in table', () => {
      render(<IPManagementTable {...defaultProps} />);
      expect(screen.getByText('192.168.1.1')).toBeInTheDocument();
    });

    it('renders reason and source', () => {
      render(<IPManagementTable {...defaultProps} />);
      const reason = screen.getByText('Malicious');
      expect(reason).toBeInTheDocument();
      expect(reason).toHaveClass('break-keep', '[overflow-wrap:anywhere]');
      expect(screen.getByText('MANUAL')).toBeInTheDocument();
    });

    it('renders country', () => {
      render(<IPManagementTable {...defaultProps} />);
      expect(screen.getByText('KR')).toBeInTheDocument();
    });

    it('shows dash for missing country', () => {
      render(<IPManagementTable {...defaultProps} data={[makeRecord({ country: undefined })]} />);
      expect(screen.getByText('-')).toBeInTheDocument();
    });

    it('renders detection count', () => {
      render(<IPManagementTable {...defaultProps} />);
      expect(screen.getByText('3')).toBeInTheDocument();
    });
  });

  describe('unified tab', () => {
    it('shows 구분 column header', () => {
      render(<IPManagementTable {...defaultProps} activeTab="unified" />);
      expect(screen.getByText('구분')).toBeInTheDocument();
    });

    it('shows 화이트 badge for whitelist type', () => {
      render(
        <IPManagementTable
          {...defaultProps}
          activeTab="unified"
          data={[makeRecord({ list_type: 'whitelist' })]}
        />
      );
      expect(screen.getByText('화이트')).toBeInTheDocument();
    });

    it('shows 블랙 badge for blacklist type', () => {
      render(
        <IPManagementTable
          {...defaultProps}
          activeTab="unified"
          data={[makeRecord({ list_type: 'blacklist' })]}
        />
      );
      expect(screen.getByText('블랙')).toBeInTheDocument();
    });

    it('hides action buttons on unified tab', () => {
      render(<IPManagementTable {...defaultProps} activeTab="unified" />);
      expect(screen.queryByText('작업')).not.toBeInTheDocument();
    });
  });

  describe('status icons', () => {
    it('shows active icon for is_active=true and auto_active=true', () => {
      render(
        <IPManagementTable
          {...defaultProps}
          data={[makeRecord({ is_active: true, auto_active: true })]}
        />
      );
      expect(screen.getByText('활성')).toBeInTheDocument();
    });

    it('shows inactive icon for is_active=true and auto_active=false', () => {
      render(
        <IPManagementTable
          {...defaultProps}
          data={[makeRecord({ is_active: true, auto_active: false })]}
        />
      );
      expect(screen.getByText('비활동')).toBeInTheDocument();
    });

    it('shows released icon for is_active=false', () => {
      render(<IPManagementTable {...defaultProps} data={[makeRecord({ is_active: false })]} />);
      expect(screen.getByText('해제')).toBeInTheDocument();
    });
  });

  describe('blacklist columns', () => {
    it('shows blacklist columns on blacklist tab', () => {
      render(<IPManagementTable {...defaultProps} activeTab="blacklist" />);
      expect(screen.getByText('상태')).toBeInTheDocument();
      expect(screen.getByText('탐지일')).toBeInTheDocument();
      expect(screen.getByText('해제일')).toBeInTheDocument();
      expect(screen.getByText('탐지횟수')).toBeInTheDocument();
    });

    it('shows blacklist columns on unified tab', () => {
      render(<IPManagementTable {...defaultProps} activeTab="unified" />);
      expect(screen.getByText('상태')).toBeInTheDocument();
    });

    it('hides blacklist columns on whitelist tab', () => {
      render(<IPManagementTable {...defaultProps} activeTab="whitelist" />);
      expect(screen.queryByText('상태')).not.toBeInTheDocument();
      expect(screen.queryByText('탐지일')).not.toBeInTheDocument();
    });

    it('shows dash for missing dates', () => {
      render(
        <IPManagementTable
          {...defaultProps}
          data={[makeRecord({ detection_date: undefined, removal_date: undefined })]}
        />
      );
      const dashes = screen.getAllByText('-');
      expect(dashes.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('actions', () => {
    it('shows edit and delete buttons on non-unified tab', () => {
      render(<IPManagementTable {...defaultProps} activeTab="blacklist" />);
      expect(screen.getByText('작업')).toBeInTheDocument();
    });

    it('calls onEdit when edit button clicked', () => {
      const onEdit = vi.fn();
      render(<IPManagementTable {...defaultProps} onEdit={onEdit} />);
      const editButtons = screen.getAllByTestId('icon-edit');
      fireEvent.click(editButtons[0].closest('button')!);
      expect(onEdit).toHaveBeenCalledWith(defaultProps.data[0]);
    });

    it('calls onDelete when delete button clicked', () => {
      const onDelete = vi.fn();
      render(<IPManagementTable {...defaultProps} onDelete={onDelete} />);
      const btn = screen.getByLabelText('192.168.1.1 삭제');
      fireEvent.click(btn);
      expect(onDelete).toHaveBeenCalledWith(defaultProps.data[0]);
    });
  });

  describe('pagination', () => {
    it('hides pagination when totalPages <= 1', () => {
      render(<IPManagementTable {...defaultProps} totalPages={1} />);
      expect(screen.queryByText('이전')).not.toBeInTheDocument();
      expect(screen.queryByText('다음')).not.toBeInTheDocument();
    });

    it('shows pagination info when totalPages > 1', () => {
      render(<IPManagementTable {...defaultProps} page={1} total={50} totalPages={3} />);
      expect(screen.getByText('총 50개 (페이지 1/3)')).toBeInTheDocument();
    });

    it('shows 다음 button on first page', () => {
      render(<IPManagementTable {...defaultProps} page={1} totalPages={3} />);
      expect(screen.queryByText('이전')).not.toBeInTheDocument();
      expect(screen.getByText('다음')).toBeInTheDocument();
    });

    it('shows 이전 button on last page', () => {
      render(<IPManagementTable {...defaultProps} page={3} totalPages={3} />);
      expect(screen.getByText('이전')).toBeInTheDocument();
      expect(screen.queryByText('다음')).not.toBeInTheDocument();
    });

    it('shows both buttons on middle page', () => {
      render(<IPManagementTable {...defaultProps} page={2} totalPages={3} />);
      expect(screen.getByText('이전')).toBeInTheDocument();
      expect(screen.getByText('다음')).toBeInTheDocument();
    });

    it('calls onPageChange with previous page', () => {
      const onPageChange = vi.fn();
      render(
        <IPManagementTable {...defaultProps} page={2} totalPages={3} onPageChange={onPageChange} />
      );
      fireEvent.click(screen.getByText('이전'));
      expect(onPageChange).toHaveBeenCalledWith(1);
    });

    it('calls onPageChange with next page', () => {
      const onPageChange = vi.fn();
      render(
        <IPManagementTable {...defaultProps} page={2} totalPages={3} onPageChange={onPageChange} />
      );
      fireEvent.click(screen.getByText('다음'));
      expect(onPageChange).toHaveBeenCalledWith(3);
    });
  });
});
