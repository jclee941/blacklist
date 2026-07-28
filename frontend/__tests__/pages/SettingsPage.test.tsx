import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import SettingsPage from '@/app/settings/page';

vi.mock('lucide-react', () => ({
  Settings: (props: Record<string, unknown>) => <svg data-testid="icon-settings" {...props} />,
  Database: (props: Record<string, unknown>) => <svg data-testid="icon-database" {...props} />,
  Shield: (props: Record<string, unknown>) => <svg data-testid="icon-shield" {...props} />,
  Bell: (props: Record<string, unknown>) => <svg data-testid="icon-bell" {...props} />,
  Cloud: (props: Record<string, unknown>) => <svg data-testid="icon-cloud" {...props} />,
  Save: (props: Record<string, unknown>) => <svg data-testid="icon-save" {...props} />,
  RefreshCw: (props: Record<string, unknown>) => <svg data-testid="icon-refresh" {...props} />,
}));

vi.mock('@/app/settings/CloudflareSettings', () => ({
  default: () => <div data-testid="cloudflare-settings">CF</div>,
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

const mockGetSettingsGrouped = vi.fn();
const mockUpdateSettingsBatch = vi.fn();

vi.mock('@/lib/api', () => ({
  default: { get: vi.fn() },
  getSettingsGrouped: () => mockGetSettingsGrouped(),
  updateSettingsBatch: (settings: Array<{ key: string; value: string }>) =>
    mockUpdateSettingsBatch(settings),
}));

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetSettingsGrouped.mockResolvedValue({
      success: true,
      settings: {
        system: [
          { key: 'auto_deactivate_expired', value: 'true' },
          { key: 'collection_interval_hours', value: '24' },
          { key: 'cache_ttl_seconds', value: '300' },
          { key: 'max_batch_size', value: '1000' },
        ],
        notifications: [
          { key: 'email_alerts', value: 'false' },
          { key: 'slack_alerts', value: 'false' },
          { key: 'alert_threshold', value: '100' },
        ],
      },
    });
    mockUpdateSettingsBatch.mockResolvedValue({ success: true, success_count: 7 });
  });

  it('renders page header', async () => {
    render(<SettingsPage />);
    expect(screen.getByText('\uc124\uc815')).toBeInTheDocument();
  });

  it('renders tabs', () => {
    render(<SettingsPage />);
    const tabsContainer = screen.getByTestId('tabs');
    expect(tabsContainer).toHaveTextContent('\uc2dc\uc2a4\ud15c \uc124\uc815');
    expect(tabsContainer).toHaveTextContent('\ub370\uc774\ud130\ubca0\uc774\uc2a4');
    expect(tabsContainer).toHaveTextContent('\ubcf4\uc548');
    expect(tabsContainer).toHaveTextContent('\uc54c\ub9bc');
  });

  it('shows system settings tab by default', () => {
    render(<SettingsPage />);
    expect(
      screen.getByText('\ud574\uc81c\uc77c \uacbd\uacfc IP \uc790\ub3d9 \ube44\ud65c\uc131\ud654')
    ).toBeInTheDocument();
  });

  it('exposes the automatic deactivation toggle with its accessible state', async () => {
    render(<SettingsPage />);

    expect(
      await screen.findByRole('switch', { name: '해제일 경과 IP 자동 비활성화' })
    ).toHaveAttribute('aria-checked', 'true');
  });

  it('shows system settings fields', () => {
    render(<SettingsPage />);
    expect(screen.getByText('\uc218\uc9d1 \uc8fc\uae30 (\uc2dc\uac04)')).toBeInTheDocument();
    expect(screen.getByText('\uce90\uc2dc TTL (\ucd08)')).toBeInTheDocument();
    expect(screen.getByText('\ubc30\uce58 \ucc98\ub9ac \ud06c\uae30')).toBeInTheDocument();
  });

  it('switches to database tab', async () => {
    render(<SettingsPage />);
    fireEvent.click(screen.getByText('\ub370\uc774\ud130\ubca0\uc774\uc2a4'));
    await waitFor(() => {
      expect(
        screen.getByText('\ub370\uc774\ud130\ubca0\uc774\uc2a4 \uc124\uc815')
      ).toBeInTheDocument();
      expect(screen.getByText('blacklist-postgres')).toBeInTheDocument();
      expect(screen.getByText('5432')).toBeInTheDocument();
    });
  });

  it('switches to security tab', async () => {
    render(<SettingsPage />);
    fireEvent.click(screen.getByText('\ubcf4\uc548'));
    await waitFor(() => {
      expect(screen.getByText('\ubcf4\uc548 \uc124\uc815')).toBeInTheDocument();
      expect(screen.getByText('CSRF \ubcf4\ud638')).toBeInTheDocument();
      expect(screen.getByText('Rate Limiting')).toBeInTheDocument();
    });
  });

  it('switches to notifications tab', async () => {
    render(<SettingsPage />);
    fireEvent.click(screen.getByText('\uc54c\ub9bc'));
    await waitFor(() => {
      expect(screen.getByText('\uc54c\ub9bc \uc124\uc815')).toBeInTheDocument();
      expect(screen.getByText('\uc774\uba54\uc77c \uc54c\ub9bc')).toBeInTheDocument();
      expect(screen.getByText('Slack \uc54c\ub9bc')).toBeInTheDocument();
    });
  });

  it('exposes notification toggles with accessible names and states', async () => {
    render(<SettingsPage />);
    fireEvent.click(screen.getByText('알림'));

    await waitFor(() => {
      expect(screen.getByRole('switch', { name: '이메일 알림' })).toHaveAttribute(
        'aria-checked',
        'false'
      );
      expect(screen.getByRole('switch', { name: 'Slack 알림' })).toHaveAttribute(
        'aria-checked',
        'false'
      );
    });
  });

  it('renders cloudflare tab', async () => {
    render(<SettingsPage />);
    fireEvent.click(screen.getByText('Cloudflare'));
    await waitFor(() => {
      expect(screen.getByTestId('cloudflare-settings')).toBeInTheDocument();
    });
  });

  it('renders save button', () => {
    render(<SettingsPage />);
    expect(screen.getByText('\uc124\uc815 \uc800\uc7a5')).toBeInTheDocument();
  });

  it('calls loadSettings on mount', async () => {
    render(<SettingsPage />);
    await waitFor(() => {
      expect(mockGetSettingsGrouped).toHaveBeenCalled();
    });
  });

  it('saves settings when save button is clicked', async () => {
    render(<SettingsPage />);
    await waitFor(() => {
      expect(mockGetSettingsGrouped).toHaveBeenCalled();
    });
    fireEvent.click(screen.getByText('\uc124\uc815 \uc800\uc7a5'));
    await waitFor(() => {
      expect(mockUpdateSettingsBatch).toHaveBeenCalled();
    });
  });

  it('shows success message after saving', async () => {
    render(<SettingsPage />);
    await waitFor(() => {
      expect(mockGetSettingsGrouped).toHaveBeenCalled();
    });
    fireEvent.click(screen.getByText('\uc124\uc815 \uc800\uc7a5'));
    await waitFor(() => {
      expect(
        screen.getByText(/\uc124\uc815\uc774 \uc800\uc7a5\ub418\uc5c8\uc2b5\ub2c8\ub2e4/)
      ).toBeInTheDocument();
    });
  });

  it('shows error message when save fails', async () => {
    mockUpdateSettingsBatch.mockResolvedValue({ success: false });
    render(<SettingsPage />);
    await waitFor(() => {
      expect(mockGetSettingsGrouped).toHaveBeenCalled();
    });
    fireEvent.click(screen.getByText('\uc124\uc815 \uc800\uc7a5'));
    await waitFor(() => {
      expect(
        screen.getByText('\uc124\uc815 \uc800\uc7a5\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.')
      ).toBeInTheDocument();
    });
  });

  it('shows error message when load fails', async () => {
    mockGetSettingsGrouped.mockRejectedValue(new Error('Load failed'));
    render(<SettingsPage />);
    await waitFor(() => {
      expect(
        screen.getByText(
          '\uc124\uc815\uc744 \ubd88\ub7ec\uc624\ub294\ub370 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.'
        )
      ).toBeInTheDocument();
    });
  });
});
