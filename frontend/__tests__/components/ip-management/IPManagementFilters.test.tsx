import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { IPManagementFilters } from '@/app/ip-management/components/IPManagementFilters';
import type { TabType } from '@/app/ip-management/components/types';

vi.mock('lucide-react', () => ({
  Search: (props: Record<string, unknown>) => <svg data-testid="icon-search" {...props} />,
  Download: (props: Record<string, unknown>) => <svg data-testid="icon-download" {...props} />,
  Plus: (props: Record<string, unknown>) => <svg data-testid="icon-plus" {...props} />,
}));

const defaultProps = {
  activeTab: 'blacklist' as TabType,
  filterType: '',
  filterSource: '',
  searchIP: '',
  isDownloading: false,
  onFilterTypeChange: vi.fn(),
  onFilterSourceChange: vi.fn(),
  onSearchIPChange: vi.fn(),
  onSearch: vi.fn(),
  onReset: vi.fn(),
  onDownload: vi.fn(),
  onAdd: vi.fn(),
};

describe('IPManagementFilters', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('filter dropdowns', () => {
    it('shows filter dropdowns on unified tab', () => {
      render(<IPManagementFilters {...defaultProps} activeTab="unified" />);
      expect(screen.getByDisplayValue('전체')).toBeInTheDocument();
    });

    it('hides filter dropdowns on non-unified tab', () => {
      render(<IPManagementFilters {...defaultProps} activeTab="blacklist" />);
      expect(screen.queryByDisplayValue('전체')).not.toBeInTheDocument();
    });

    it('calls onFilterTypeChange', () => {
      const onFilterTypeChange = vi.fn();
      render(
        <IPManagementFilters
          {...defaultProps}
          activeTab="unified"
          onFilterTypeChange={onFilterTypeChange}
        />
      );
      const typeSelect = screen.getByDisplayValue('전체');
      fireEvent.change(typeSelect, { target: { value: 'whitelist' } });
      expect(onFilterTypeChange).toHaveBeenCalledWith('whitelist');
    });
  });

  describe('search', () => {
    it('renders search input', () => {
      render(<IPManagementFilters {...defaultProps} />);
      expect(screen.getByPlaceholderText('IP 주소 검색...')).toBeInTheDocument();
    });

    it('calls onSearchIPChange on input', () => {
      const onSearchIPChange = vi.fn();
      render(<IPManagementFilters {...defaultProps} onSearchIPChange={onSearchIPChange} />);
      fireEvent.change(screen.getByPlaceholderText('IP 주소 검색...'), {
        target: { value: '10.0' },
      });
      expect(onSearchIPChange).toHaveBeenCalledWith('10.0');
    });

    it('calls onSearch on Enter key', () => {
      const onSearch = vi.fn();
      render(<IPManagementFilters {...defaultProps} onSearch={onSearch} />);
      fireEvent.keyPress(screen.getByPlaceholderText('IP 주소 검색...'), {
        key: 'Enter',
        charCode: 13,
      });
      expect(onSearch).toHaveBeenCalled();
    });

    it('calls onSearch on search button click', () => {
      const onSearch = vi.fn();
      render(<IPManagementFilters {...defaultProps} onSearch={onSearch} />);
      fireEvent.click(screen.getByTestId('icon-search').closest('button')!);
      expect(onSearch).toHaveBeenCalled();
    });
  });

  describe('reset button', () => {
    it('hides reset when searchIP is empty', () => {
      render(<IPManagementFilters {...defaultProps} searchIP="" />);
      expect(screen.queryByText('초기화')).not.toBeInTheDocument();
    });

    it('shows reset when searchIP is non-empty', () => {
      render(<IPManagementFilters {...defaultProps} searchIP="192" />);
      expect(screen.getByText('초기화')).toBeInTheDocument();
    });

    it('calls onReset when clicked', () => {
      const onReset = vi.fn();
      render(<IPManagementFilters {...defaultProps} searchIP="192" onReset={onReset} />);
      fireEvent.click(screen.getByText('초기화'));
      expect(onReset).toHaveBeenCalled();
    });
  });

  describe('download button', () => {
    it('shows Raw Data text', () => {
      render(<IPManagementFilters {...defaultProps} />);
      expect(screen.getByText('Raw Data')).toBeInTheDocument();
    });

    it('shows downloading text when isDownloading', () => {
      render(<IPManagementFilters {...defaultProps} isDownloading={true} />);
      expect(screen.getByText('다운로드 중...')).toBeInTheDocument();
    });

    it('calls onDownload when clicked', () => {
      const onDownload = vi.fn();
      render(<IPManagementFilters {...defaultProps} onDownload={onDownload} />);
      fireEvent.click(screen.getByText('Raw Data'));
      expect(onDownload).toHaveBeenCalled();
    });

    it('is disabled when downloading', () => {
      render(<IPManagementFilters {...defaultProps} isDownloading={true} />);
      expect(screen.getByText('다운로드 중...').closest('button')).toBeDisabled();
    });
  });

  describe('add button', () => {
    it('shows add button on non-unified tabs', () => {
      render(<IPManagementFilters {...defaultProps} activeTab="blacklist" />);
      expect(screen.getByText('추가')).toBeInTheDocument();
    });

    it('hides add button on unified tab', () => {
      render(<IPManagementFilters {...defaultProps} activeTab="unified" />);
      expect(screen.queryByText('추가')).not.toBeInTheDocument();
    });

    it('calls onAdd when clicked', () => {
      const onAdd = vi.fn();
      render(<IPManagementFilters {...defaultProps} activeTab="blacklist" onAdd={onAdd} />);
      fireEvent.click(screen.getByText('추가'));
      expect(onAdd).toHaveBeenCalled();
    });
  });
});
