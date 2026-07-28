import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CredentialEditModal } from '@/app/collection/components/CredentialEditModal';
import type { CredentialFormState } from '@/app/collection/components/types';

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

vi.mock('@/components/ui/Input', () => ({
  default: ({
    label,
    value,
    onChange,
    error,
    placeholder,
    type,
    required,
  }: {
    label: string;
    value: string;
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    error?: string;
    placeholder?: string;
    type?: string;
    required?: boolean;
  }) => (
    <div>
      <label>
        {label}
        {required && '*'}
      </label>
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        type={type || 'text'}
        aria-label={label}
      />
      {error && <span data-testid={`error-${label}`}>{error}</span>}
    </div>
  ),
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

describe('CredentialEditModal', () => {
  const defaultForm: CredentialFormState = {
    username: 'testuser',
    password: '',
    enabled: true,
    collection_interval: 'hourly',
  };

  const defaultProps = {
    show: true,
    onClose: vi.fn(),
    editingService: 'REGTECH',
    credentialForm: defaultForm,
    configured: true,
    onFormChange: vi.fn(),
    onSave: vi.fn(),
    loading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when show is false', () => {
    const { container } = render(<CredentialEditModal {...defaultProps} show={false} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders modal with service name in title', () => {
    render(<CredentialEditModal {...defaultProps} />);
    expect(screen.getByText('REGTECH 설정 및 저장')).toBeInTheDocument();
  });

  it('renders common fields: username, password, collection interval', () => {
    render(<CredentialEditModal {...defaultProps} />);
    expect(screen.getByLabelText('사용자명')).toBeInTheDocument();
    expect(screen.getByLabelText('비밀번호')).toBeInTheDocument();
    expect(screen.getByLabelText('수집 주기')).toBeInTheDocument();
  });

  it('renders enabled checkbox', () => {
    render(<CredentialEditModal {...defaultProps} />);
    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeChecked();
  });

  it('calls onFormChange when username changes', () => {
    render(<CredentialEditModal {...defaultProps} />);
    fireEvent.change(screen.getByLabelText('사용자명'), {
      target: { value: 'newuser' },
    });
    expect(defaultProps.onFormChange).toHaveBeenCalledWith(
      expect.objectContaining({ username: 'newuser' })
    );
  });

  it('calls onFormChange when password changes', () => {
    render(<CredentialEditModal {...defaultProps} />);
    fireEvent.change(screen.getByLabelText('비밀번호'), {
      target: { value: 'newpass' },
    });
    expect(defaultProps.onFormChange).toHaveBeenCalledWith(
      expect.objectContaining({ password: 'newpass' })
    );
  });

  it('offers only backend-supported collection intervals and updates the selected value', () => {
    render(<CredentialEditModal {...defaultProps} />);
    const intervalSelect = screen.getByLabelText('수집 주기');

    expect(screen.getAllByRole('option').map((option) => option.getAttribute('value'))).toEqual([
      'hourly',
      'daily',
      'weekly',
    ]);

    fireEvent.change(intervalSelect, {
      target: { value: 'weekly' },
    });
    expect(defaultProps.onFormChange).toHaveBeenCalledWith(
      expect.objectContaining({ collection_interval: 'weekly' })
    );
  });

  it('calls onFormChange when enabled checkbox toggles', () => {
    render(<CredentialEditModal {...defaultProps} />);
    fireEvent.click(screen.getByRole('checkbox'));
    expect(defaultProps.onFormChange).toHaveBeenCalledWith(
      expect.objectContaining({ enabled: false })
    );
  });

  it('calls onClose when cancel button is clicked', () => {
    render(<CredentialEditModal {...defaultProps} />);
    fireEvent.click(screen.getByText('취소'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('calls onSave when save button is clicked with valid form', () => {
    render(<CredentialEditModal {...defaultProps} />);
    fireEvent.click(screen.getByText('설정 및 저장'));
    expect(defaultProps.onSave).toHaveBeenCalled();
  });

  it('disables save button when loading', () => {
    render(<CredentialEditModal {...defaultProps} loading={true} />);
    expect(screen.getByText('Loading...')).toBeDisabled();
  });

  it('shows validation error only after saving an invalid username', () => {
    const emptyUsernameForm = { ...defaultForm, username: '' };
    render(<CredentialEditModal {...defaultProps} credentialForm={emptyUsernameForm} />);

    expect(screen.queryByTestId('error-사용자명')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('설정 및 저장'));

    expect(screen.getByTestId('error-사용자명')).toHaveTextContent('사용자명을 입력하세요');
    expect(defaultProps.onSave).not.toHaveBeenCalled();
  });

  it('requires a password after saving unconfigured credentials', () => {
    render(<CredentialEditModal {...defaultProps} configured={false} />);

    expect(screen.queryByTestId('error-비밀번호')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('설정 및 저장'));

    expect(screen.getByTestId('error-비밀번호')).toHaveTextContent('비밀번호를 입력하세요');
    expect(defaultProps.onSave).not.toHaveBeenCalled();
  });
});
