import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import LoginPage from '@/app/login/page';

const { mockReplace, mockLogin } = vi.hoisted(() => ({
  mockReplace: vi.fn(),
  mockLogin: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace }),
}));

vi.mock('@/lib/api', () => ({
  login: mockLogin,
}));

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submits credentials and replaces the route after a successful login', async () => {
    mockLogin.mockResolvedValue({ token: 'jwt-token' });
    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText(/사용자명/), { target: { value: 'admin' } });
    fireEvent.change(screen.getByLabelText(/비밀번호/), { target: { value: 'password' } });
    fireEvent.click(screen.getByRole('button', { name: '로그인' }));

    await waitFor(() => expect(mockLogin).toHaveBeenCalledWith('admin', 'password'));
    expect(mockReplace).toHaveBeenCalledWith('/');
  });

  it('shows an authentication error when login fails', async () => {
    mockLogin.mockRejectedValue(new Error('Unauthorized'));
    render(<LoginPage />);

    fireEvent.change(screen.getByLabelText(/사용자명/), { target: { value: 'admin' } });
    fireEvent.change(screen.getByLabelText(/비밀번호/), { target: { value: 'wrong-password' } });
    fireEvent.click(screen.getByRole('button', { name: '로그인' }));

    expect(
      await screen.findByText('로그인에 실패했습니다. 사용자명과 비밀번호를 확인하세요.')
    ).toBeInTheDocument();
  });
});
