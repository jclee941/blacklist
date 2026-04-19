import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import CloudflareSettings from '@/app/settings/CloudflareSettings';

vi.mock('lucide-react', () => ({
  Cloud: () => <div data-testid="icon-cloud" />,
  CheckCircle: () => <div data-testid="icon-check" />,
  XCircle: () => <div data-testid="icon-x" />,
  Loader2: () => <div data-testid="icon-loader" />,
}));

vi.mock('@/lib/api', () => ({
  getCloudflareCredentials: vi.fn(),
  saveCloudflareCredentials: vi.fn(),
  testCloudflareConnection: vi.fn(),
}));

import {
  getCloudflareCredentials,
  saveCloudflareCredentials,
  testCloudflareConnection,
} from '@/lib/api';

describe('CloudflareSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getCloudflareCredentials).mockResolvedValue({
      success: true,
      data: {
        password: '***masked***',
        config: {
          account_id: 'acct-123',
          list_id: 'list-456',
        },
      },
    });
    vi.mocked(saveCloudflareCredentials).mockResolvedValue({
      success: true,
      data: { message: 'Credentials updated for CLOUDFLARE' },
    });
    vi.mocked(testCloudflareConnection).mockResolvedValue({
      success: true,
      data: { message: 'Cloudflare connection successful' },
    });
  });

  it('loads saved cloudflare credential fields from response data', async () => {
    render(<CloudflareSettings />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('acct-123')).toBeInTheDocument();
    });

    expect(screen.getByDisplayValue('list-456')).toBeInTheDocument();
    expect(screen.getByDisplayValue('••••••••')).toBeInTheDocument();
  });

  it('allows saving updated ids while keeping a masked token', async () => {
    render(<CloudflareSettings />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('acct-123')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText('Account ID'), { target: { value: 'acct-updated' } });
    fireEvent.change(screen.getByLabelText('List ID'), { target: { value: 'list-updated' } });
    fireEvent.click(screen.getByRole('button', { name: '저장' }));

    await waitFor(() => {
      expect(saveCloudflareCredentials).toHaveBeenCalledWith({
        api_token: '••••••••',
        account_id: 'acct-updated',
        list_id: 'list-updated',
      });
    });

    expect(screen.getByText('Credentials updated for CLOUDFLARE')).toBeInTheDocument();
  });

  it('shows API error messages from nested test response data', async () => {
    vi.mocked(testCloudflareConnection).mockResolvedValueOnce({
      success: false,
      data: { message: 'Cloudflare connection failed' },
    });

    render(<CloudflareSettings />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('acct-123')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: '연결 테스트' }));

    await waitFor(() => {
      expect(testCloudflareConnection).toHaveBeenCalled();
    });

    expect(screen.getByText('Cloudflare connection failed')).toBeInTheDocument();
  });
});
