import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import OtpInputDialog from '@/app/collection/components/OtpInputDialog';

vi.mock('@/components/ui/Modal', () => ({
  default: ({
    isOpen,
    onClose,
    title,
    children,
  }: {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: React.ReactNode;
  }) =>
    isOpen ? (
      <div data-testid="modal">
        <h2>{title}</h2>
        <button onClick={onClose} type="button">
          close
        </button>
        {children}
      </div>
    ) : null,
}));

vi.mock('@/components/ui/Button', () => ({
  default: ({
    children,
    onClick,
    loading,
    disabled,
    variant,
    type,
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    loading?: boolean;
    disabled?: boolean;
    variant?: string;
    type?: string;
  }) => (
    <button
      onClick={onClick}
      disabled={!!disabled || !!loading}
      data-variant={variant}
      type={type === 'submit' ? 'submit' : 'button'}
    >
      {loading ? 'Loading...' : children}
    </button>
  ),
}));

describe('OtpInputDialog', () => {
  const defaultProps = {
    show: true,
    onClose: vi.fn(),
    onSubmit: vi.fn(),
    loading: false,
    serviceName: 'SECUDIUM',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when show is false', () => {
    const { container } = render(<OtpInputDialog {...defaultProps} show={false} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders modal with OTP title', () => {
    render(<OtpInputDialog {...defaultProps} />);
    expect(screen.getByText('OTP 인증')).toBeInTheDocument();
  });

  it('displays simplified instruction text', () => {
    render(<OtpInputDialog {...defaultProps} />);
    expect(screen.getByText(/OTP를 입력해주세요/)).toBeInTheDocument();
  });

  it('renders OTP input with maxLength 6', () => {
    render(<OtpInputDialog {...defaultProps} />);
    const input = screen.getByPlaceholderText('000000');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('maxLength', '6');
  });

  it('filters non-numeric characters from OTP input', () => {
    render(<OtpInputDialog {...defaultProps} />);
    const input = screen.getByPlaceholderText('000000');
    fireEvent.change(input, { target: { value: 'abc123' } });
    expect(input).toHaveValue('123');
  });

  it('accepts valid 6-digit OTP input', () => {
    render(<OtpInputDialog {...defaultProps} />);
    const input = screen.getByPlaceholderText('000000');
    fireEvent.change(input, { target: { value: '123456' } });
    expect(input).toHaveValue('123456');
  });

  it('disables submit button when OTP is not 6 digits', () => {
    render(<OtpInputDialog {...defaultProps} />);
    const submitBtn = screen.getByText('확인');
    expect(submitBtn).toBeDisabled();
  });

  it('enables submit button when OTP is exactly 6 digits', () => {
    render(<OtpInputDialog {...defaultProps} />);
    const input = screen.getByPlaceholderText('000000');
    fireEvent.change(input, { target: { value: '123456' } });
    const submitBtn = screen.getByText('확인');
    expect(submitBtn).not.toBeDisabled();
  });

  it('calls onSubmit with OTP code on form submit', () => {
    render(<OtpInputDialog {...defaultProps} />);
    const input = screen.getByPlaceholderText('000000');
    fireEvent.change(input, { target: { value: '654321' } });
    fireEvent.submit(screen.getByText('확인').closest('form')!);
    expect(defaultProps.onSubmit).toHaveBeenCalledWith('654321');
  });

  it('does not call onSubmit when OTP is less than 6 digits', () => {
    render(<OtpInputDialog {...defaultProps} />);
    const input = screen.getByPlaceholderText('000000');
    fireEvent.change(input, { target: { value: '123' } });
    fireEvent.submit(screen.getByText('확인').closest('form')!);
    expect(defaultProps.onSubmit).not.toHaveBeenCalled();
  });

  it('calls onClose when cancel button is clicked', () => {
    render(<OtpInputDialog {...defaultProps} />);
    fireEvent.click(screen.getByText('취소'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('disables input when loading', () => {
    render(<OtpInputDialog {...defaultProps} loading={true} />);
    const input = screen.getByPlaceholderText('000000');
    expect(input).toBeDisabled();
  });

  it('disables cancel button when loading', () => {
    render(<OtpInputDialog {...defaultProps} loading={true} />);
    expect(screen.getByText('취소')).toBeDisabled();
  });

  it('shows loading state on submit button when loading', () => {
    render(<OtpInputDialog {...defaultProps} loading={true} />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
});
