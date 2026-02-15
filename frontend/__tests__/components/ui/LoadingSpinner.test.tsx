import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

// Mock lucide-react — spread props so className flows through
vi.mock('lucide-react', () => ({
  RefreshCw: (props: Record<string, unknown>) => <svg data-testid="icon-refresh" {...props} />,
}));

describe('LoadingSpinner', () => {
  it('renders with default message', () => {
    render(<LoadingSpinner />);
    expect(screen.getByText('로딩 중...')).toBeInTheDocument();
  });

  it('renders with custom message', () => {
    render(<LoadingSpinner message="데이터 로딩 중" />);
    expect(screen.getByText('데이터 로딩 중')).toBeInTheDocument();
  });

  it('renders spinner icon', () => {
    render(<LoadingSpinner />);
    expect(screen.getByTestId('icon-refresh')).toBeInTheDocument();
  });

  it('applies md size by default', () => {
    render(<LoadingSpinner />);
    const icon = screen.getByTestId('icon-refresh');
    const cls = icon.getAttribute('class') ?? '';
    expect(cls).toContain('h-8');
    expect(cls).toContain('w-8');
  });

  it('applies sm size', () => {
    render(<LoadingSpinner size="sm" />);
    const icon = screen.getByTestId('icon-refresh');
    const cls = icon.getAttribute('class') ?? '';
    expect(cls).toContain('h-5');
    expect(cls).toContain('w-5');
  });

  it('applies lg size', () => {
    render(<LoadingSpinner size="lg" />);
    const icon = screen.getByTestId('icon-refresh');
    const cls = icon.getAttribute('class') ?? '';
    expect(cls).toContain('h-12');
    expect(cls).toContain('w-12');
  });

  it('has spin animation class', () => {
    render(<LoadingSpinner />);
    const icon = screen.getByTestId('icon-refresh');
    const cls = icon.getAttribute('class') ?? '';
    expect(cls).toContain('animate-spin');
  });

  it('hides message when empty string', () => {
    const { container } = render(<LoadingSpinner message="" />);
    expect(container.querySelectorAll('span')).toHaveLength(0);
  });
});
