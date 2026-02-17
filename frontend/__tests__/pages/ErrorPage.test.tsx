import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorPage from '@/app/error';

vi.mock('lucide-react', () => ({
  AlertTriangle: (props: Record<string, unknown>) => <svg data-testid="icon-alert" {...props} />,
  RefreshCw: (props: Record<string, unknown>) => <svg data-testid="icon-refresh" {...props} />,
  Home: (props: Record<string, unknown>) => <svg data-testid="icon-home" {...props} />,
}));

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

describe('ErrorPage', () => {
  const mockReset = vi.fn();
  const mockError = Object.assign(
    new globalThis.Error('Test error message'),
    {}
  ) as globalThis.Error & { digest?: string };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('renders error heading', () => {
    render(<ErrorPage error={mockError} reset={mockReset} />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('renders error description', () => {
    render(<ErrorPage error={mockError} reset={mockReset} />);
    expect(
      screen.getByText('An unexpected error occurred. Please try again or return to the home page.')
    ).toBeInTheDocument();
  });

  it('renders Try again button', () => {
    render(<ErrorPage error={mockError} reset={mockReset} />);
    expect(screen.getByText('Try again')).toBeInTheDocument();
  });

  it('calls reset when Try again is clicked', () => {
    render(<ErrorPage error={mockError} reset={mockReset} />);
    fireEvent.click(screen.getByText('Try again'));
    expect(mockReset).toHaveBeenCalled();
  });

  it('renders Go home link pointing to /', () => {
    render(<ErrorPage error={mockError} reset={mockReset} />);
    const homeLink = screen.getByText('Go home').closest('a');
    expect(homeLink).toHaveAttribute('href', '/');
  });

  it('logs error to console on mount', () => {
    render(<ErrorPage error={mockError} reset={mockReset} />);
    expect(console.error).toHaveBeenCalledWith('Application error:', mockError);
  });
});
