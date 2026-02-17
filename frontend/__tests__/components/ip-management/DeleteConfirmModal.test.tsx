import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DeleteConfirmModal } from '@/app/ip-management/components/DeleteConfirmModal';
import type { IPRecord } from '@/app/ip-management/components/types';

const mockRecord: IPRecord = {
  id: 1,
  ip_address: '10.0.0.1',
  reason: 'Test',
  source: 'MANUAL',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

const defaultProps = {
  isOpen: true,
  record: mockRecord,
  onConfirm: vi.fn(),
  onClose: vi.fn(),
};

describe('DeleteConfirmModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('visibility', () => {
    it('returns null when not open', () => {
      const { container } = render(<DeleteConfirmModal {...defaultProps} isOpen={false} />);
      expect(container.innerHTML).toBe('');
    });

    it('returns null when record is null', () => {
      const { container } = render(<DeleteConfirmModal {...defaultProps} record={null} />);
      expect(container.innerHTML).toBe('');
    });

    it('renders when open with record', () => {
      render(<DeleteConfirmModal {...defaultProps} />);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  describe('content', () => {
    it('shows 삭제 확인 title', () => {
      render(<DeleteConfirmModal {...defaultProps} />);
      expect(screen.getByText('삭제 확인')).toBeInTheDocument();
    });

    it('shows IP address in confirmation text', () => {
      render(<DeleteConfirmModal {...defaultProps} />);
      expect(screen.getByText('10.0.0.1')).toBeInTheDocument();
    });
  });

  describe('buttons', () => {
    it('calls onConfirm when 삭제 clicked', () => {
      const onConfirm = vi.fn();
      render(<DeleteConfirmModal {...defaultProps} onConfirm={onConfirm} />);
      fireEvent.click(screen.getByText('삭제'));
      expect(onConfirm).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when 취소 clicked', () => {
      const onClose = vi.fn();
      render(<DeleteConfirmModal {...defaultProps} onClose={onClose} />);
      fireEvent.click(screen.getByText('취소'));
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('backdrop', () => {
    it('calls onClose when backdrop clicked', () => {
      const onClose = vi.fn();
      render(<DeleteConfirmModal {...defaultProps} onClose={onClose} />);
      // Click on the backdrop (outer div)
      const backdrop = screen.getByRole('dialog').parentElement!;
      fireEvent.click(backdrop);
      expect(onClose).toHaveBeenCalled();
    });

    it('does not close when inner dialog clicked', () => {
      const onClose = vi.fn();
      render(<DeleteConfirmModal {...defaultProps} onClose={onClose} />);
      fireEvent.click(screen.getByRole('dialog'));
      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe('escape key', () => {
    it('calls onClose on Escape key', () => {
      const onClose = vi.fn();
      render(<DeleteConfirmModal {...defaultProps} onClose={onClose} />);
      const backdrop = screen.getByRole('dialog').parentElement!;
      fireEvent.keyDown(backdrop, { key: 'Escape' });
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('accessibility', () => {
    it('has role=dialog and aria-modal', () => {
      render(<DeleteConfirmModal {...defaultProps} />);
      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
    });

    it('has aria-labelledby', () => {
      render(<DeleteConfirmModal {...defaultProps} />);
      expect(screen.getByRole('dialog').getAttribute('aria-labelledby')).toBe('delete-modal-title');
    });
  });
});
