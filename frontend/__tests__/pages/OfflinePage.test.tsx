import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { OfflineIndicator } from '@/app/offline';

vi.mock('lucide-react', () => ({
  WifiOff: (props: Record<string, unknown>) => <svg data-testid="icon-wifi-off" {...props} />,
}));

describe('OfflineIndicator', () => {
  let addEventListenerSpy: ReturnType<typeof vi.spyOn>;
  let removeEventListenerSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(navigator, 'onLine', {
      value: true,
      writable: true,
      configurable: true,
    });
    addEventListenerSpy = vi.spyOn(window, 'addEventListener');
    removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');
  });

  it('renders nothing when online', () => {
    const { container } = render(<OfflineIndicator />);
    expect(container.innerHTML).toBe('');
  });

  it('renders offline indicator when navigator.onLine is false', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: false,
      writable: true,
      configurable: true,
    });
    render(<OfflineIndicator />);
    expect(screen.getByText('\uc624\ud504\ub77c\uc778 \ubaa8\ub4dc')).toBeInTheDocument();
  });

  it('shows offline indicator when offline event fires', () => {
    render(<OfflineIndicator />);
    expect(screen.queryByText('\uc624\ud504\ub77c\uc778 \ubaa8\ub4dc')).not.toBeInTheDocument();

    act(() => {
      window.dispatchEvent(new Event('offline'));
    });

    expect(screen.getByText('\uc624\ud504\ub77c\uc778 \ubaa8\ub4dc')).toBeInTheDocument();
  });

  it('hides offline indicator when online event fires', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: false,
      writable: true,
      configurable: true,
    });
    render(<OfflineIndicator />);
    expect(screen.getByText('\uc624\ud504\ub77c\uc778 \ubaa8\ub4dc')).toBeInTheDocument();

    act(() => {
      window.dispatchEvent(new Event('online'));
    });

    expect(screen.queryByText('\uc624\ud504\ub77c\uc778 \ubaa8\ub4dc')).not.toBeInTheDocument();
  });

  it('registers online/offline event listeners', () => {
    render(<OfflineIndicator />);
    expect(addEventListenerSpy).toHaveBeenCalledWith('online', expect.any(Function));
    expect(addEventListenerSpy).toHaveBeenCalledWith('offline', expect.any(Function));
  });

  it('cleans up event listeners on unmount', () => {
    const { unmount } = render(<OfflineIndicator />);
    unmount();
    expect(removeEventListenerSpy).toHaveBeenCalledWith('online', expect.any(Function));
    expect(removeEventListenerSpy).toHaveBeenCalledWith('offline', expect.any(Function));
  });

  it('renders WifiOff icon when offline', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: false,
      writable: true,
      configurable: true,
    });
    render(<OfflineIndicator />);
    expect(screen.getByTestId('icon-wifi-off')).toBeInTheDocument();
  });
});
