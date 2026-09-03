import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  login: vi.fn(),
  replace: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mocks.replace }),
}));

vi.mock('@/lib/api', () => ({
  login: mocks.login,
}));

import LoginPage from '@/app/login/page';

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submits labeled administrator credentials and opens the dashboard', async () => {
    const user = userEvent.setup();
    mocks.login.mockResolvedValue({ token: 'valid-token' });
    render(<LoginPage />);

    const username = screen.getByLabelText('관리자 아이디');
    const password = screen.getByLabelText('비밀번호');
    expect(username).toBeRequired();
    expect(password).toBeRequired();

    await user.type(username, 'admin');
    await user.type(password, 'secret-password');
    await user.click(screen.getByRole('button', { name: '로그인' }));

    expect(mocks.login).toHaveBeenCalledWith('admin', 'secret-password');
    expect(mocks.replace).toHaveBeenCalledWith('/');
  });

  it('uses POST for the native pre-hydration fallback', () => {
    render(<LoginPage />);

    expect(screen.getByRole('button', { name: '로그인' }).closest('form')).toHaveAttribute(
      'method',
      'post'
    );
  });

  it('keeps the form visible and announces invalid credentials', async () => {
    const user = userEvent.setup();
    mocks.login.mockRejectedValue(new Error('invalid credentials'));
    render(<LoginPage />);

    await user.type(screen.getByLabelText('관리자 아이디'), 'admin');
    await user.type(screen.getByLabelText('비밀번호'), 'wrong-password');
    await user.click(screen.getByRole('button', { name: '로그인' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      '아이디 또는 비밀번호를 확인해 주세요.'
    );
    expect(mocks.replace).not.toHaveBeenCalled();
  });
});
