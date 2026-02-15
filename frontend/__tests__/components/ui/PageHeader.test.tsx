import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import PageHeader from '@/components/ui/PageHeader';

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Shield: (props: Record<string, unknown>) => <svg data-testid="icon-shield" {...props} />,
}));

describe('PageHeader', () => {
  it('renders title', () => {
    render(<PageHeader title="Dashboard" description="Overview of the system" />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('renders description', () => {
    render(<PageHeader title="Dashboard" description="Overview" />);
    expect(screen.getByText('Overview')).toBeInTheDocument();
  });

  it('renders icon when provided', async () => {
    const { Shield } = await import('lucide-react');
    render(<PageHeader title="Security" description="Desc" icon={Shield as never} />);
    expect(screen.getByTestId('icon-shield')).toBeInTheDocument();
  });

  it('does not render icon container when no icon', () => {
    const { container } = render(<PageHeader title="Title" description="Desc" />);
    expect(container.querySelector('.bg-gradient-to-br')).not.toBeInTheDocument();
  });

  it('renders actions when provided', () => {
    render(
      <PageHeader
        title="Title"
        description="Desc"
        actions={<button type="button">Add New</button>}
      />
    );
    expect(screen.getByText('Add New')).toBeInTheDocument();
  });

  it('does not render actions container when not provided', () => {
    const { container } = render(<PageHeader title="Title" description="Desc" />);
    // Only the title/description section should exist
    const flexContainers = container.querySelectorAll('.flex.items-center.space-x-3');
    expect(flexContainers).toHaveLength(0);
  });

  it('renders title as h1', () => {
    render(<PageHeader title="Main Title" description="Desc" />);
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Main Title');
  });
});
