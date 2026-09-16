import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  verifyToken: vi.fn(),
  pathname: '/',
}));

vi.mock('next/navigation', () => ({
  usePathname: () => mocks.pathname,
  useRouter: () => ({ replace: mocks.replace }),
}));

vi.mock('@/lib/api', () => ({
  AUTH_UNAUTHORIZED_EVENT: 'blacklist:auth-unauthorized',
  verifyToken: mocks.verifyToken,
}));

import { AuthGate } from '@/components/AuthGate';

describe('AuthGate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.pathname = '/';
  });

  it('redirects an unauthenticated visitor without rendering protected content', async () => {
    mocks.verifyToken.mockRejectedValue(new Error('no session cookie'));

    render(
      <AuthGate>
        <div>보호된 대시보드</div>
      </AuthGate>
    );

    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith('/login'));
    expect(screen.queryByText('보호된 대시보드')).not.toBeInTheDocument();
  });

  it('renders protected content after token verification', async () => {
    mocks.verifyToken.mockResolvedValue({ valid: true });

    render(
      <AuthGate>
        <div>보호된 대시보드</div>
      </AuthGate>
    );

    expect(await screen.findByText('보호된 대시보드')).toBeInTheDocument();
  });

  it('redirects to login when the session is rejected', async () => {
    mocks.verifyToken.mockRejectedValue(new Error('expired'));

    render(
      <AuthGate>
        <div>보호된 대시보드</div>
      </AuthGate>
    );

    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith('/login'));
    expect(screen.queryByText('보호된 대시보드')).not.toBeInTheDocument();
  });

  it('returns to login when the API reports an expired session', async () => {
    mocks.verifyToken.mockResolvedValue({ valid: true });

    render(
      <AuthGate>
        <div>보호된 대시보드</div>
      </AuthGate>
    );
    expect(await screen.findByText('보호된 대시보드')).toBeInTheDocument();

    window.dispatchEvent(new Event('blacklist:auth-unauthorized'));

    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith('/login'));
    expect(screen.queryByText('보호된 대시보드')).not.toBeInTheDocument();
  });

  it('renders the public login route without token verification', () => {
    mocks.pathname = '/login';

    render(
      <AuthGate>
        <div>관리자 로그인</div>
      </AuthGate>
    );

    expect(screen.getByText('관리자 로그인')).toBeInTheDocument();
    expect(mocks.verifyToken).not.toHaveBeenCalled();
  });
});
