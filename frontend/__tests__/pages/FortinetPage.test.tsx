import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import FortinetPage from '@/app/fortinet/page';

vi.mock('lucide-react', () => ({
  Shield: (props: Record<string, unknown>) => <svg data-testid="icon-shield" {...props} />,
}));

vi.mock('@/app/fortinet/FortinetClient', () => ({
  default: () => <div data-testid="fortinet-client">FortinetClient</div>,
}));

vi.mock('@/components/ui/PageHeader', () => ({
  default: ({ title, description }: { title: string; description: string }) => (
    <div data-testid="page-header">
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  ),
}));

vi.mock('@/components/ui/LoadingSpinner', () => ({
  default: ({ message }: { message: string }) => <div data-testid="loading-spinner">{message}</div>,
}));

describe('FortinetPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page header with title', () => {
    render(<FortinetPage />);
    expect(screen.getByText('FortiGate 연동')).toBeInTheDocument();
  });

  it('renders page header with description', () => {
    render(<FortinetPage />);
    expect(screen.getByText('FortiGate 방화벽 블랙리스트 연동 관리')).toBeInTheDocument();
  });

  it('renders FortinetClient component', () => {
    render(<FortinetPage />);
    expect(screen.getByTestId('fortinet-client')).toBeInTheDocument();
  });

  it('wraps content in main element', () => {
    render(<FortinetPage />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
