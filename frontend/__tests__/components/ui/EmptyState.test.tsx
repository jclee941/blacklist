import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import EmptyState from '@/components/ui/EmptyState';

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Inbox: (props: Record<string, unknown>) => <svg data-testid="icon-inbox" {...props} />,
  Search: (props: Record<string, unknown>) => <svg data-testid="icon-search" {...props} />,
}));

describe('EmptyState', () => {
  it('renders title', () => {
    render(<EmptyState title="No data found" />);
    expect(screen.getByText('No data found')).toBeInTheDocument();
  });

  it('renders description when provided', () => {
    render(<EmptyState title="Empty" description="Try a different search" />);
    expect(screen.getByText('Try a different search')).toBeInTheDocument();
  });

  it('does not render description when not provided', () => {
    const { container } = render(<EmptyState title="Empty" />);
    const paragraphs = container.querySelectorAll('p.text-gray-500');
    expect(paragraphs).toHaveLength(0);
  });

  it('renders default icon (Inbox)', () => {
    render(<EmptyState title="Empty" />);
    expect(screen.getByTestId('icon-inbox')).toBeInTheDocument();
  });

  it('renders custom icon', async () => {
    const { Search } = await import('lucide-react');
    render(<EmptyState title="No results" icon={Search as never} />);
    expect(screen.getByTestId('icon-search')).toBeInTheDocument();
  });

  it('renders action element when provided', () => {
    render(<EmptyState title="Empty" action={<button type="button">Add new</button>} />);
    expect(screen.getByText('Add new')).toBeInTheDocument();
  });

  it('does not render action when not provided', () => {
    const { container } = render(<EmptyState title="Empty" />);
    expect(container.querySelectorAll('button')).toHaveLength(0);
  });
});
