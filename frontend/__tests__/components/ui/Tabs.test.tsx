import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Tabs from '@/components/ui/Tabs';

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Home: (props: Record<string, unknown>) => <svg data-testid="icon-home" {...props} />,
  Settings: (props: Record<string, unknown>) => <svg data-testid="icon-settings" {...props} />,
}));

const baseTabs = [
  { id: 'tab1', label: 'Tab 1' },
  { id: 'tab2', label: 'Tab 2' },
  { id: 'tab3', label: 'Tab 3' },
];

describe('Tabs', () => {
  const defaultProps = {
    tabs: baseTabs,
    activeTab: 'tab1',
    onChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('renders all tab labels', () => {
      render(<Tabs {...defaultProps} />);
      expect(screen.getByText('Tab 1')).toBeInTheDocument();
      expect(screen.getByText('Tab 2')).toBeInTheDocument();
      expect(screen.getByText('Tab 3')).toBeInTheDocument();
    });

    it('renders with tablist role', () => {
      render(<Tabs {...defaultProps} />);
      expect(screen.getByRole('tablist')).toBeInTheDocument();
    });

    it('renders each tab with tab role', () => {
      render(<Tabs {...defaultProps} />);
      const tabs = screen.getAllByRole('tab');
      expect(tabs).toHaveLength(3);
    });
  });

  describe('ARIA attributes', () => {
    it('sets aria-selected true for active tab', () => {
      render(<Tabs {...defaultProps} activeTab="tab2" />);
      const tabs = screen.getAllByRole('tab');
      expect(tabs[0]).toHaveAttribute('aria-selected', 'false');
      expect(tabs[1]).toHaveAttribute('aria-selected', 'true');
      expect(tabs[2]).toHaveAttribute('aria-selected', 'false');
    });

    it('sets aria-controls for each tab', () => {
      render(<Tabs {...defaultProps} />);
      const tabs = screen.getAllByRole('tab');
      expect(tabs[0]).toHaveAttribute('aria-controls', 'panel-tab1');
      expect(tabs[1]).toHaveAttribute('aria-controls', 'panel-tab2');
    });

    it('sets aria-label on tablist', () => {
      render(<Tabs {...defaultProps} aria-label="My tabs" />);
      expect(screen.getByRole('tablist')).toHaveAttribute('aria-label', 'My tabs');
    });

    it('uses default aria-label', () => {
      render(<Tabs {...defaultProps} />);
      expect(screen.getByRole('tablist')).toHaveAttribute('aria-label', 'Tabs');
    });
  });

  describe('onChange', () => {
    it('calls onChange with tab id on click', () => {
      const onChange = vi.fn();
      render(<Tabs {...defaultProps} onChange={onChange} />);
      fireEvent.click(screen.getByText('Tab 2'));
      expect(onChange).toHaveBeenCalledWith('tab2');
    });

    it('calls onChange with correct id for third tab', () => {
      const onChange = vi.fn();
      render(<Tabs {...defaultProps} onChange={onChange} />);
      fireEvent.click(screen.getByText('Tab 3'));
      expect(onChange).toHaveBeenCalledWith('tab3');
    });
  });

  describe('variants', () => {
    it('renders underline variant by default', () => {
      const { container } = render(<Tabs {...defaultProps} />);
      expect(container.querySelector('.border-b')).toBeInTheDocument();
    });

    it('renders pills variant', () => {
      render(<Tabs {...defaultProps} variant="pills" activeTab="tab1" />);
      const activeTab = screen.getByText('Tab 1');
      expect(activeTab.className).toContain('bg-blue-500');
      expect(activeTab.className).toContain('text-white');
    });

    it('renders boxed variant', () => {
      const { container } = render(<Tabs {...defaultProps} variant="boxed" />);
      expect(container.querySelector('.shadow-lg')).toBeInTheDocument();
    });

    it('pills inactive tab has gray background', () => {
      render(<Tabs {...defaultProps} variant="pills" activeTab="tab1" />);
      const inactiveTab = screen.getByText('Tab 2');
      expect(inactiveTab.className).toContain('bg-gray-100');
    });

    it('boxed active tab has blue styling', () => {
      render(<Tabs {...defaultProps} variant="boxed" activeTab="tab1" />);
      const activeTab = screen.getByText('Tab 1');
      expect(activeTab.className).toContain('bg-blue-50');
      expect(activeTab.className).toContain('text-blue-700');
    });
  });

  describe('icons', () => {
    it('renders icons when provided', async () => {
      const { Home, Settings } = await import('lucide-react');
      const tabsWithIcons = [
        { id: 'tab1', label: 'Home', icon: Home as never },
        { id: 'tab2', label: 'Settings', icon: Settings as never },
      ];
      render(<Tabs tabs={tabsWithIcons} activeTab="tab1" onChange={vi.fn()} />);
      expect(screen.getByTestId('icon-home')).toBeInTheDocument();
      expect(screen.getByTestId('icon-settings')).toBeInTheDocument();
    });
  });

  describe('data-testid', () => {
    it('applies custom data-testid', () => {
      render(<Tabs {...defaultProps} data-testid="my-tabs" />);
      expect(screen.getByTestId('my-tabs')).toBeInTheDocument();
    });

    it('uses default data-testid', () => {
      render(<Tabs {...defaultProps} />);
      expect(screen.getByTestId('tabs')).toBeInTheDocument();
    });
  });
});
