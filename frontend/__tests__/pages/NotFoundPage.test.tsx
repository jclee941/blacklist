import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import NotFound from '@/app/not-found';

vi.mock('lucide-react', () => ({
  FileQuestion: (props: Record<string, unknown>) => (
    <svg data-testid="icon-file-question" {...props} />
  ),
  Home: (props: Record<string, unknown>) => <svg data-testid="icon-home" {...props} />,
  ArrowLeft: (props: Record<string, unknown>) => <svg data-testid="icon-arrow-left" {...props} />,
}));

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

describe('NotFoundPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders 404 heading', () => {
    render(<NotFound />);
    expect(
      screen.getByText('\ud398\uc774\uc9c0\ub97c \ucc3e\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4')
    ).toBeInTheDocument();
  });

  it('renders description text', () => {
    render(<NotFound />);
    expect(
      screen.getByText(
        '\uc694\uccad\ud558\uc2e0 \ud398\uc774\uc9c0\uac00 \uc874\uc7ac\ud558\uc9c0 \uc54a\uac70\ub098 \uc774\ub3d9\ub418\uc5c8\uc2b5\ub2c8\ub2e4.'
      )
    ).toBeInTheDocument();
  });

  it('renders 404 Not Found text', () => {
    render(<NotFound />);
    expect(screen.getByText('404 Not Found')).toBeInTheDocument();
  });

  it('renders home link pointing to /', () => {
    render(<NotFound />);
    const homeLink = screen.getByText('\ud648\uc73c\ub85c \uc774\ub3d9').closest('a');
    expect(homeLink).toHaveAttribute('href', '/');
  });

  it('renders back button', () => {
    render(<NotFound />);
    expect(screen.getByText('\uc774\uc804 \ud398\uc774\uc9c0')).toBeInTheDocument();
  });

  it('calls history.back when back button is clicked', () => {
    const mockBack = vi.fn();
    vi.spyOn(window.history, 'back').mockImplementation(mockBack);
    render(<NotFound />);
    fireEvent.click(screen.getByText('\uc774\uc804 \ud398\uc774\uc9c0'));
    expect(mockBack).toHaveBeenCalled();
  });
});
