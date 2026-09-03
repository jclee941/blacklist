import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Modal from '@/components/ui/Modal';

// Mock lucide-react
vi.mock('lucide-react', () => ({
  X: (props: Record<string, unknown>) => <svg data-testid="icon-x" {...props} />,
}));

describe('Modal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    children: <div>Modal content</div>,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    document.body.style.overflow = '';
  });

  afterEach(() => {
    document.body.style.overflow = '';
  });

  describe('visibility', () => {
    it('renders children when open', () => {
      render(<Modal {...defaultProps} />);
      expect(screen.getByText('Modal content')).toBeInTheDocument();
    });

    it('renders nothing when closed', () => {
      render(<Modal {...defaultProps} isOpen={false} />);
      expect(screen.queryByText('Modal content')).not.toBeInTheDocument();
    });
  });

  describe('dialog accessibility', () => {
    it('traps focus in the dialog and restores the triggering focus when closed', () => {
      const trigger = document.createElement('button');
      document.body.appendChild(trigger);
      trigger.focus();

      const { unmount } = render(
        <Modal {...defaultProps} title="Test Title">
          <button type="button">First action</button>
          <button type="button">Last action</button>
        </Modal>
      );

      const dialog = screen.getByRole('dialog');
      const closeButton = screen.getByLabelText('Close');
      const lastAction = screen.getByRole('button', { name: 'Last action' });

      expect(dialog).toHaveAttribute('aria-modal', 'true');
      expect(dialog).toHaveAttribute('aria-labelledby');

      lastAction.focus();
      fireEvent.keyDown(lastAction, { key: 'Tab' });
      expect(closeButton).toHaveFocus();

      unmount();
      expect(trigger).toHaveFocus();
      trigger.remove();
    });

    it('cycles backward from the dialog container to the last action', () => {
      render(
        <Modal {...defaultProps} title="Test Title">
          <button type="button">First action</button>
          <button type="button">Last action</button>
        </Modal>
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveFocus();
      fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true });
      expect(screen.getByRole('button', { name: 'Last action' })).toHaveFocus();
    });

    it('preserves focused fields when the onClose callback changes', () => {
      const { rerender } = render(
        <Modal {...defaultProps} onClose={vi.fn()}>
          <input aria-label="Editable field" />
        </Modal>
      );
      const field = screen.getByLabelText('Editable field');
      field.focus();

      rerender(
        <Modal {...defaultProps} onClose={vi.fn()}>
          <input aria-label="Editable field" />
        </Modal>
      );

      expect(field).toHaveFocus();
    });

    it('restores focus to the trigger from each open cycle', () => {
      const firstTrigger = document.createElement('button');
      const secondTrigger = document.createElement('button');
      document.body.append(firstTrigger, secondTrigger);
      firstTrigger.focus();
      const { rerender } = render(<Modal {...defaultProps} />);

      rerender(<Modal {...defaultProps} isOpen={false} />);
      expect(firstTrigger).toHaveFocus();
      secondTrigger.focus();
      rerender(<Modal {...defaultProps} />);
      rerender(<Modal {...defaultProps} isOpen={false} />);

      expect(secondTrigger).toHaveFocus();
      firstTrigger.remove();
      secondTrigger.remove();
    });
  });

  describe('title', () => {
    it('renders title when provided', () => {
      render(<Modal {...defaultProps} title="Test Title" />);
      expect(screen.getByText('Test Title')).toBeInTheDocument();
    });

    it('renders without title', () => {
      render(<Modal {...defaultProps} />);
      expect(screen.queryByRole('heading')).not.toBeInTheDocument();
    });
  });

  describe('close button', () => {
    it('shows close button by default', () => {
      render(<Modal {...defaultProps} title="Title" />);
      expect(screen.getByLabelText('Close')).toBeInTheDocument();
    });

    it('hides close button when showCloseButton is false', () => {
      render(<Modal {...defaultProps} title="Title" showCloseButton={false} />);
      expect(screen.queryByLabelText('Close')).not.toBeInTheDocument();
    });

    it('calls onClose when close button clicked', () => {
      const onClose = vi.fn();
      render(<Modal {...defaultProps} onClose={onClose} title="Title" />);
      fireEvent.click(screen.getByLabelText('Close'));
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('backdrop', () => {
    it('calls onClose when backdrop clicked', () => {
      const onClose = vi.fn();
      render(<Modal {...defaultProps} onClose={onClose} />);
      fireEvent.click(screen.getByLabelText('Close modal backdrop'));
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('escape key', () => {
    it('calls onClose on Escape key', () => {
      const onClose = vi.fn();
      render(<Modal {...defaultProps} onClose={onClose} />);
      fireEvent.keyDown(document, { key: 'Escape' });
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('does not call onClose on other keys', () => {
      const onClose = vi.fn();
      render(<Modal {...defaultProps} onClose={onClose} />);
      fireEvent.keyDown(document, { key: 'Enter' });
      expect(onClose).not.toHaveBeenCalled();
    });
  });

  describe('body overflow', () => {
    it('locks body scroll when open', () => {
      render(<Modal {...defaultProps} />);
      expect(document.body.style.overflow).toBe('hidden');
    });

    it('restores body scroll on unmount', () => {
      const { unmount } = render(<Modal {...defaultProps} />);
      expect(document.body.style.overflow).toBe('hidden');
      unmount();
      expect(document.body.style.overflow).toBe('');
    });
  });

  describe('size variants', () => {
    it('applies md size class by default', () => {
      const { container } = render(<Modal {...defaultProps} />);
      const modalContent = container.querySelector('.max-w-md');
      expect(modalContent).toBeInTheDocument();
    });

    it.each(['sm', 'md', 'lg', 'xl'] as const)('applies %s size class', (size) => {
      const { container } = render(<Modal {...defaultProps} size={size} />);
      const modalContent = container.querySelector(`.max-w-${size}`);
      expect(modalContent).toBeInTheDocument();
    });
  });
});
