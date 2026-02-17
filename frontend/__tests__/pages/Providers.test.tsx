import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Providers } from '@/app/providers';

vi.mock('@tanstack/react-query', () => {
  const QueryClientProvider = ({ children }: { children: React.ReactNode; client: unknown }) => (
    <div data-testid="query-client-provider">{children}</div>
  );

  class QueryClient {
    constructor(public options?: Record<string, unknown>) {}
  }

  return { QueryClientProvider, QueryClient };
});

describe('Providers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children within QueryClientProvider', () => {
    render(
      <Providers>
        <div data-testid="child">Child content</div>
      </Providers>
    );
    expect(screen.getByTestId('query-client-provider')).toBeInTheDocument();
    expect(screen.getByTestId('child')).toBeInTheDocument();
    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('renders multiple children', () => {
    render(
      <Providers>
        <div data-testid="child-1">First</div>
        <div data-testid="child-2">Second</div>
      </Providers>
    );
    expect(screen.getByTestId('child-1')).toBeInTheDocument();
    expect(screen.getByTestId('child-2')).toBeInTheDocument();
  });

  it('wraps children in QueryClientProvider', () => {
    render(
      <Providers>
        <span>Nested</span>
      </Providers>
    );
    const provider = screen.getByTestId('query-client-provider');
    expect(provider).toContainElement(screen.getByText('Nested'));
  });
});
