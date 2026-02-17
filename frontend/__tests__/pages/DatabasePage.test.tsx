import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import DatabasePage from '@/app/database/page';

vi.mock('lucide-react', () => ({
  Database: (props: Record<string, unknown>) => <svg data-testid="icon-database" {...props} />,
}));

vi.mock('@/app/database/DatabaseOverviewClient', () => ({
  default: () => <div data-testid="database-client">DatabaseOverviewClient</div>,
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

describe('DatabasePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page header with title', () => {
    render(<DatabasePage />);
    expect(screen.getByText('데이터베이스')).toBeInTheDocument();
  });

  it('renders page header with description', () => {
    render(<DatabasePage />);
    expect(screen.getByText('PostgreSQL 테이블 현황')).toBeInTheDocument();
  });

  it('renders DatabaseOverviewClient component', () => {
    render(<DatabasePage />);
    expect(screen.getByTestId('database-client')).toBeInTheDocument();
  });

  it('wraps content in main element', () => {
    render(<DatabasePage />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
