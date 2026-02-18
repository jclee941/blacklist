import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { IPManagementFormModal } from '@/app/ip-management/components/IPManagementFormModal';
import type { IPFormData, TabType } from '@/app/ip-management/components/types';

const makeFormData = (overrides: Partial<IPFormData> = {}): IPFormData => ({
  ip_address: '',
  reason: '',
  source: 'MANUAL',
  country: '',
  is_active: true,
  detection_date: '',
  removal_date: '',
  ...overrides,
});

const defaultProps = {
  isOpen: true,
  isEdit: false,
  activeTab: 'blacklist' as TabType,
  listType: 'blacklist' as const,
  formData: makeFormData(),
  isSubmitting: false,
  onFormChange: vi.fn(),
  onSubmit: vi.fn(),
  onClose: vi.fn(),
};

describe('IPManagementFormModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('visibility', () => {
    it('returns null when not open', () => {
      const { container } = render(<IPManagementFormModal {...defaultProps} isOpen={false} />);
      expect(container.innerHTML).toBe('');
    });

    it('renders when open', () => {
      render(<IPManagementFormModal {...defaultProps} />);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  describe('title', () => {
    it('shows add title for blacklist tab', () => {
      render(<IPManagementFormModal {...defaultProps} isEdit={false} activeTab="blacklist" />);
      expect(screen.getByText('블랙리스트 추가')).toBeInTheDocument();
    });

    it('shows add title for whitelist tab', () => {
      render(
        <IPManagementFormModal
          {...defaultProps}
          isEdit={false}
          activeTab="whitelist"
          listType="whitelist"
        />
      );
      expect(screen.getByText('화이트리스트 추가')).toBeInTheDocument();
    });

    it('shows edit title for whitelist', () => {
      render(<IPManagementFormModal {...defaultProps} isEdit={true} listType="whitelist" />);
      expect(screen.getByText('화이트리스트 수정')).toBeInTheDocument();
    });

    it('shows edit title for blacklist', () => {
      render(<IPManagementFormModal {...defaultProps} isEdit={true} listType="blacklist" />);
      expect(screen.getByText('블랙리스트 수정')).toBeInTheDocument();
    });
  });

  describe('form fields', () => {
    it('renders IP address input', () => {
      render(<IPManagementFormModal {...defaultProps} />);
      expect(screen.getByPlaceholderText('192.168.1.1')).toBeInTheDocument();
    });

    it('calls onFormChange on IP input', () => {
      const onFormChange = vi.fn();
      render(<IPManagementFormModal {...defaultProps} onFormChange={onFormChange} />);
      fireEvent.change(screen.getByPlaceholderText('192.168.1.1'), {
        target: { value: '10.0.0.1' },
      });
      expect(onFormChange).toHaveBeenCalled();
    });

    it('renders reason input', () => {
      render(<IPManagementFormModal {...defaultProps} activeTab="blacklist" />);
      expect(screen.getByPlaceholderText('악성 활동')).toBeInTheDocument();
    });

    it('renders whitelist placeholder for reason on whitelist tab', () => {
      render(
        <IPManagementFormModal {...defaultProps} activeTab="whitelist" listType="whitelist" />
      );
      expect(screen.getByPlaceholderText('VIP 고객')).toBeInTheDocument();
    });

    it('renders source dropdown with 4 options', () => {
      render(<IPManagementFormModal {...defaultProps} />);
      const select = screen.getByDisplayValue('수동 입력');
      expect(select).toBeInTheDocument();
      expect(select.querySelectorAll('option')).toHaveLength(4);
    });

    it('shows country field only in edit mode', () => {
      const { rerender } = render(<IPManagementFormModal {...defaultProps} isEdit={false} />);
      expect(screen.queryByText('국가 코드')).not.toBeInTheDocument();

      rerender(<IPManagementFormModal {...defaultProps} isEdit={true} />);
      expect(screen.getByText('국가 코드')).toBeInTheDocument();
    });
  });

  describe('blacklist-specific fields', () => {
    it('shows blacklist fields when listType is blacklist', () => {
      render(<IPManagementFormModal {...defaultProps} listType="blacklist" />);
      expect(screen.getByText('활성화')).toBeInTheDocument();
    });

    it('shows blacklist fields when activeTab is blacklist', () => {
      render(
        <IPManagementFormModal {...defaultProps} activeTab="blacklist" listType="whitelist" />
      );
      expect(screen.getByText('활성화')).toBeInTheDocument();
    });

    it('hides blacklist fields for whitelist on whitelist tab', () => {
      render(
        <IPManagementFormModal {...defaultProps} activeTab="whitelist" listType="whitelist" />
      );
      expect(screen.queryByText('활성화')).not.toBeInTheDocument();
    });

    it('auto-calculates removal date from detection date', () => {
      const onFormChange = vi.fn();
      render(<IPManagementFormModal {...defaultProps} onFormChange={onFormChange} />);
      const detectionInput = screen.getByLabelText(/^탐지일/);
      fireEvent.change(detectionInput, { target: { value: '2025-01-15' } });
      expect(onFormChange).toHaveBeenCalledWith(
        expect.objectContaining({
          detection_date: '2025-01-15',
          removal_date: '2025-04-15',
        })
      );
    });
  });

  describe('submit button', () => {
    it('shows 추가 text when not editing', () => {
      render(<IPManagementFormModal {...defaultProps} isEdit={false} />);
      expect(screen.getByText('추가')).toBeInTheDocument();
    });

    it('shows 수정 text when editing', () => {
      render(<IPManagementFormModal {...defaultProps} isEdit={true} />);
      expect(screen.getByText('수정')).toBeInTheDocument();
    });

    it('shows spinner text when submitting (add)', () => {
      render(<IPManagementFormModal {...defaultProps} isSubmitting={true} isEdit={false} />);
      expect(screen.getByText('추가 중...')).toBeInTheDocument();
    });

    it('shows spinner text when submitting (edit)', () => {
      render(<IPManagementFormModal {...defaultProps} isSubmitting={true} isEdit={true} />);
      expect(screen.getByText('수정 중...')).toBeInTheDocument();
    });

    it('calls onSubmit when clicked', () => {
      const onSubmit = vi.fn();
      render(<IPManagementFormModal {...defaultProps} onSubmit={onSubmit} />);
      fireEvent.click(screen.getByText('추가'));
      expect(onSubmit).toHaveBeenCalled();
    });

    it('is disabled when submitting', () => {
      render(<IPManagementFormModal {...defaultProps} isSubmitting={true} />);
      const submitBtn = screen.getByText('추가 중...').closest('button');
      expect(submitBtn).toBeDisabled();
    });
  });

  describe('cancel button', () => {
    it('calls onClose when clicked', () => {
      const onClose = vi.fn();
      render(<IPManagementFormModal {...defaultProps} onClose={onClose} />);
      fireEvent.click(screen.getByText('취소'));
      expect(onClose).toHaveBeenCalled();
    });

    it('is disabled when submitting', () => {
      render(<IPManagementFormModal {...defaultProps} isSubmitting={true} />);
      expect(screen.getByText('취소')).toBeDisabled();
    });
  });

  describe('escape key', () => {
    it('calls onClose on Escape when not submitting', () => {
      const onClose = vi.fn();
      render(<IPManagementFormModal {...defaultProps} onClose={onClose} />);
      fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
      expect(onClose).toHaveBeenCalled();
    });

    it('does not call onClose on Escape when submitting', () => {
      const onClose = vi.fn();
      render(<IPManagementFormModal {...defaultProps} onClose={onClose} isSubmitting={true} />);
      fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe('accessibility', () => {
    it('has role=dialog and aria-modal', () => {
      render(<IPManagementFormModal {...defaultProps} />);
      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
    });

    it('has aria-labelledby pointing to title', () => {
      render(<IPManagementFormModal {...defaultProps} />);
      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-labelledby', 'form-modal-title');
    });
  });
});
