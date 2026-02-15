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
      expect(document.body.style.overflow).toBe('unset');
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
