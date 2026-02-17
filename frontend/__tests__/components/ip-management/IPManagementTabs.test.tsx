import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { IPManagementTabs } from '@/app/ip-management/components/IPManagementTabs';
import type { TabType } from '@/app/ip-management/components/types';

vi.mock('lucide-react', () => ({
  Layers: (props: Record<string, unknown>) => <svg data-testid="icon-layers" {...props} />,
  ShieldCheck: (props: Record<string, unknown>) => (
    <svg data-testid="icon-shield-check" {...props} />
  ),
  ShieldAlert: (props: Record<string, unknown>) => (
    <svg data-testid="icon-shield-alert" {...props} />
  ),
}));

describe('IPManagementTabs', () => {
  const onTabChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all three tabs', () => {
    render(<IPManagementTabs activeTab="unified" onTabChange={onTabChange} />);
    expect(screen.getByText('통합 뷰')).toBeInTheDocument();
    expect(screen.getByText('화이트리스트')).toBeInTheDocument();
    expect(screen.getByText('블랙리스트')).toBeInTheDocument();
  });

  it('applies active class to unified tab', () => {
    render(<IPManagementTabs activeTab="unified" onTabChange={onTabChange} />);
    const tab = screen.getByText('통합 뷰').closest('button');
    expect(tab?.className).toContain('border-blue-500');
  });

  it('applies active class to whitelist tab', () => {
    render(<IPManagementTabs activeTab="whitelist" onTabChange={onTabChange} />);
    const tab = screen.getByText('화이트리스트').closest('button');
    expect(tab?.className).toContain('border-green-500');
  });

  it('applies active class to blacklist tab', () => {
    render(<IPManagementTabs activeTab="blacklist" onTabChange={onTabChange} />);
    const tab = screen.getByText('블랙리스트').closest('button');
    expect(tab?.className).toContain('border-red-500');
  });

  it('applies inactive class to non-active tabs', () => {
    render(<IPManagementTabs activeTab="unified" onTabChange={onTabChange} />);
    const tab = screen.getByText('화이트리스트').closest('button');
    expect(tab?.className).toContain('border-transparent');
  });

  it('calls onTabChange with unified', () => {
    render(<IPManagementTabs activeTab="blacklist" onTabChange={onTabChange} />);
    fireEvent.click(screen.getByText('통합 뷰'));
    expect(onTabChange).toHaveBeenCalledWith('unified');
  });

  it('calls onTabChange with whitelist', () => {
    render(<IPManagementTabs activeTab="unified" onTabChange={onTabChange} />);
    fireEvent.click(screen.getByText('화이트리스트'));
    expect(onTabChange).toHaveBeenCalledWith('whitelist');
  });

  it('calls onTabChange with blacklist', () => {
    render(<IPManagementTabs activeTab="unified" onTabChange={onTabChange} />);
    fireEvent.click(screen.getByText('블랙리스트'));
    expect(onTabChange).toHaveBeenCalledWith('blacklist');
  });

  it('renders icons for each tab', () => {
    render(<IPManagementTabs activeTab="unified" onTabChange={onTabChange} />);
    expect(screen.getByTestId('icon-layers')).toBeInTheDocument();
    expect(screen.getByTestId('icon-shield-check')).toBeInTheDocument();
    expect(screen.getByTestId('icon-shield-alert')).toBeInTheDocument();
  });
});
