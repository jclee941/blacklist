import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CollectionPage from '@/app/collection/page';

vi.mock('lucide-react', () => ({
  Settings: (props: Record<string, unknown>) => <svg data-testid="icon-settings" {...props} />,
  History: (props: Record<string, unknown>) => <svg data-testid="icon-history" {...props} />,
  Database: (props: Record<string, unknown>) => <svg data-testid="icon-database" {...props} />,
}));

vi.mock('@/app/collection/CollectionManagementClient', () => ({
  default: () => <div data-testid="management-client">CollectionManagementClient</div>,
}));

vi.mock('@/app/collection/CollectionHistoryClient', () => ({
  default: () => <div data-testid="history-client">CollectionHistoryClient</div>,
}));

vi.mock('@/components/ui/PageHeader', () => ({
  default: ({ title, description }: { title: string; description: string }) => (
    <div data-testid="page-header">
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  ),
}));

vi.mock('@/components/ui/Tabs', () => ({
  default: ({
    tabs,
    activeTab,
    onChange,
  }: {
    tabs: Array<{ id: string; label: string }>;
    activeTab: string;
    onChange: (id: string) => void;
  }) => (
    <div data-testid="tabs">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          data-active={tab.id === activeTab}
        >
          {tab.label}
        </button>
      ))}
    </div>
  ),
}));

vi.mock('@/components/ui/LoadingSpinner', () => ({
  default: ({ message }: { message: string }) => <div data-testid="loading-spinner">{message}</div>,
}));

describe('CollectionPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page header with title', () => {
    render(<CollectionPage />);
    expect(screen.getByText('데이터 수집')).toBeInTheDocument();
  });

  it('renders page header with description', () => {
    render(<CollectionPage />);
    expect(screen.getByText('블랙리스트 데이터 수집 관리 및 이력')).toBeInTheDocument();
  });

  it('renders tabs with 수집 관리 and 수집 이력', () => {
    render(<CollectionPage />);
    expect(screen.getByText('수집 관리')).toBeInTheDocument();
    expect(screen.getByText('수집 이력')).toBeInTheDocument();
  });

  it('renders management client by default', () => {
    render(<CollectionPage />);
    expect(screen.getByTestId('management-client')).toBeInTheDocument();
    expect(screen.queryByTestId('history-client')).not.toBeInTheDocument();
  });

  it('switches to history client when 수집 이력 tab is clicked', () => {
    render(<CollectionPage />);
    fireEvent.click(screen.getByText('수집 이력'));
    expect(screen.getByTestId('history-client')).toBeInTheDocument();
    expect(screen.queryByTestId('management-client')).not.toBeInTheDocument();
  });

  it('switches back to management client when 수집 관리 tab is clicked', () => {
    render(<CollectionPage />);
    fireEvent.click(screen.getByText('수집 이력'));
    fireEvent.click(screen.getByText('수집 관리'));
    expect(screen.getByTestId('management-client')).toBeInTheDocument();
  });

  it('wraps content in main element', () => {
    render(<CollectionPage />);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
