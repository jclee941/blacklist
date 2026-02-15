import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Card, CardHeader, StatCard } from '@/components/ui/Card';

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Shield: (props: Record<string, unknown>) => <svg data-testid="icon-shield" {...props} />,
  Activity: (props: Record<string, unknown>) => <svg data-testid="icon-activity" {...props} />,
}));

describe('Card', () => {
  it('renders children', () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('applies default md padding', () => {
    const { container } = render(<Card>Content</Card>);
    expect(container.firstChild).toHaveClass('p-6');
  });

  it('applies sm padding', () => {
    const { container } = render(<Card padding="sm">Content</Card>);
    expect(container.firstChild).toHaveClass('p-4');
  });

  it('applies lg padding', () => {
    const { container } = render(<Card padding="lg">Content</Card>);
    expect(container.firstChild).toHaveClass('p-8');
  });

  it('applies no padding', () => {
    const { container } = render(<Card padding="none">Content</Card>);
    const el = container.firstChild as HTMLElement;
    expect(el.className).not.toContain('p-4');
    expect(el.className).not.toContain('p-6');
    expect(el.className).not.toContain('p-8');
  });

  it('applies custom className', () => {
    const { container } = render(<Card className="custom-class">Content</Card>);
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('has rounded and shadow classes', () => {
    const { container } = render(<Card>Content</Card>);
    expect(container.firstChild).toHaveClass('rounded-xl');
    expect(container.firstChild).toHaveClass('shadow-lg');
  });

  it('applies data-testid', () => {
    render(<Card data-testid="my-card">Content</Card>);
    expect(screen.getByTestId('my-card')).toBeInTheDocument();
  });
});

describe('CardHeader', () => {
  it('renders title', () => {
    render(<CardHeader title="Test Title" />);
    expect(screen.getByText('Test Title')).toBeInTheDocument();
  });

  it('renders subtitle when provided', () => {
    render(<CardHeader title="Title" subtitle="Subtitle text" />);
    expect(screen.getByText('Subtitle text')).toBeInTheDocument();
  });

  it('does not render subtitle when not provided', () => {
    const { container } = render(<CardHeader title="Title" />);
    expect(container.querySelectorAll('p.text-sm.text-gray-500')).toHaveLength(0);
  });

  it('renders icon when provided', async () => {
    const { Shield } = await import('lucide-react');
    render(<CardHeader title="Title" icon={Shield as never} />);
    expect(screen.getByTestId('icon-shield')).toBeInTheDocument();
  });

  it('renders actions when provided', () => {
    render(<CardHeader title="Title" actions={<button type="button">Action</button>} />);
    expect(screen.getByText('Action')).toBeInTheDocument();
  });
});

describe('StatCard', () => {
  it('renders title and value', async () => {
    const { Activity } = await import('lucide-react');
    render(<StatCard title="Total" value={1234} icon={Activity as never} />);
    expect(screen.getByText('Total')).toBeInTheDocument();
    expect(screen.getByText('1,234')).toBeInTheDocument();
  });

  it('renders string value as-is', async () => {
    const { Activity } = await import('lucide-react');
    render(<StatCard title="Status" value="Active" icon={Activity as never} />);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('shows loading skeleton when loading', async () => {
    const { Activity } = await import('lucide-react');
    const { container } = render(
      <StatCard title="Total" value={0} icon={Activity as never} loading />
    );
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    expect(screen.queryByText('Total')).not.toBeInTheDocument();
  });

  it('renders positive trend', async () => {
    const { Activity } = await import('lucide-react');
    render(
      <StatCard
        title="Count"
        value={100}
        icon={Activity as never}
        trend={{ value: 5, isPositive: true }}
      />
    );
    expect(screen.getByText('+5%')).toBeInTheDocument();
  });

  it('renders negative trend', async () => {
    const { Activity } = await import('lucide-react');
    render(
      <StatCard
        title="Count"
        value={100}
        icon={Activity as never}
        trend={{ value: 3, isPositive: false }}
      />
    );
    expect(screen.getByText('3%')).toBeInTheDocument();
  });

  it('applies data-testid', async () => {
    const { Activity } = await import('lucide-react');
    render(<StatCard title="Test" value={0} icon={Activity as never} data-testid="stat" />);
    expect(screen.getByTestId('stat')).toBeInTheDocument();
  });
});
