import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import IPManagementPage from '@/app/ip-management/page';

vi.mock('lucide-react', () => ({
  Shield: (props: Record<string, unknown>) => <svg data-testid="icon-shield" {...props} />,
}));

vi.mock('@/app/ip-management/IPManagementClient', () => ({
  default: () => <div data-testid="ip-management-client">IPManagementClient</div>,
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

describe('IPManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page header with title', () => {
    render(<IPManagementPage />);
    expect(screen.getByText('IP 관리')).toBeInTheDocument();
  });

  it('renders page header with description', () => {
    render(<IPManagementPage />);
    expect(screen.getByText('화이트리스트 및 블랙리스트 통합 관리')).toBeInTheDocument();
  });

  it('renders IPManagementClient component', () => {
    render(<IPManagementPage />);
    expect(screen.getByTestId('ip-management-client')).toBeInTheDocument();
  });

  it('wraps content in main element', () => {
    render(<IPManagementPage />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
