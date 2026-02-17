import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CredentialEditModal } from '@/app/collection/components/CredentialEditModal';
import type {
  CredentialFormState,
  SecudiumCredentialFormState,
} from '@/app/collection/components/types';

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
    collection_interval: '3600',
  };

  const secudiumForm: SecudiumCredentialFormState = {
    username: 'secuser',
    password: '',
    enabled: true,
    collection_interval: '3600',
    otp_mode: 'auto',
    email: 'test@kakao.com',
    email_password: 'emailpass',
    imap_server: 'imap.kakao.com',
  };

  const defaultProps = {
    show: true,
    onClose: vi.fn(),
    editingService: 'REGTECH',
    credentialForm: defaultForm,
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
    expect(screen.getByText('REGTECH 인증정보 수정')).toBeInTheDocument();
  });

  it('renders common fields: username, password, collection interval', () => {
    render(<CredentialEditModal {...defaultProps} />);
    expect(screen.getByLabelText('사용자명')).toBeInTheDocument();
    expect(screen.getByLabelText('비밀번호')).toBeInTheDocument();
    expect(screen.getByLabelText('수집 주기 (초)')).toBeInTheDocument();
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

  it('calls onFormChange when collection interval changes', () => {
    render(<CredentialEditModal {...defaultProps} />);
    fireEvent.change(screen.getByLabelText('수집 주기 (초)'), {
      target: { value: '7200' },
    });
    expect(defaultProps.onFormChange).toHaveBeenCalledWith(
      expect.objectContaining({ collection_interval: '7200' })
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
    fireEvent.click(screen.getByText('저장'));
    expect(defaultProps.onSave).toHaveBeenCalled();
  });

  it('disables save button when loading', () => {
    render(<CredentialEditModal {...defaultProps} loading={true} />);
    expect(screen.getByText('Loading...')).toBeDisabled();
  });

  it('shows validation error when username is empty', () => {
    const emptyUsernameForm = { ...defaultForm, username: '' };
    render(<CredentialEditModal {...defaultProps} credentialForm={emptyUsernameForm} />);
    expect(screen.getByTestId('error-사용자명')).toHaveTextContent('사용자명을 입력하세요');
  });

  it('disables save button when form is invalid (empty username)', () => {
    const emptyUsernameForm = { ...defaultForm, username: '' };
    render(<CredentialEditModal {...defaultProps} credentialForm={emptyUsernameForm} />);
    expect(screen.getByText('저장')).toBeDisabled();
  });

  describe('SECUDIUM-specific fields', () => {
    const secudiumProps = {
      ...defaultProps,
      editingService: 'SECUDIUM',
      credentialForm: secudiumForm,
    };

    it('renders OTP mode buttons for SECUDIUM', () => {
      render(<CredentialEditModal {...secudiumProps} />);
      expect(screen.getByText('자동 (이메일 OTP)')).toBeInTheDocument();
      expect(screen.getByText('수동 (직접 입력)')).toBeInTheDocument();
    });

    it('renders email fields in auto OTP mode', () => {
      render(<CredentialEditModal {...secudiumProps} />);
      expect(screen.getByLabelText('이메일 (카카오 계정)')).toBeInTheDocument();
      expect(screen.getByLabelText('이메일 비밀번호')).toBeInTheDocument();
      expect(screen.getByLabelText('IMAP 서버')).toBeInTheDocument();
    });

    it('shows manual mode info text when manual is selected', () => {
      const manualForm = { ...secudiumForm, otp_mode: 'manual' as const };
      render(<CredentialEditModal {...secudiumProps} credentialForm={manualForm} />);
      expect(screen.getByText(/카카오톡으로 받은 OTP 번호를 직접 입력합니다/)).toBeInTheDocument();
    });

    it('does not render email fields in manual mode', () => {
      const manualForm = { ...secudiumForm, otp_mode: 'manual' as const };
      render(<CredentialEditModal {...secudiumProps} credentialForm={manualForm} />);
      expect(screen.queryByLabelText('이메일 (카카오 계정)')).not.toBeInTheDocument();
    });

    it('calls onFormChange when OTP mode switches to manual', () => {
      render(<CredentialEditModal {...secudiumProps} />);
      fireEvent.click(screen.getByText('수동 (직접 입력)'));
      expect(secudiumProps.onFormChange).toHaveBeenCalledWith(
        expect.objectContaining({ otp_mode: 'manual' })
      );
    });

    it('validates email in auto mode - empty email', () => {
      const noEmailForm = { ...secudiumForm, email: '' };
      render(<CredentialEditModal {...secudiumProps} credentialForm={noEmailForm} />);
      expect(screen.getByTestId('error-이메일 (카카오 계정)')).toHaveTextContent(
        '이메일을 입력하세요'
      );
    });

    it('validates email in auto mode - invalid format', () => {
      const badEmailForm = { ...secudiumForm, email: 'notanemail' };
      render(<CredentialEditModal {...secudiumProps} credentialForm={badEmailForm} />);
      expect(screen.getByTestId('error-이메일 (카카오 계정)')).toHaveTextContent(
        '올바른 이메일 형식이 아닙니다'
      );
    });

    it('validates email password in auto mode - empty', () => {
      const noPassForm = { ...secudiumForm, email_password: '' };
      render(<CredentialEditModal {...secudiumProps} credentialForm={noPassForm} />);
      expect(screen.getByTestId('error-이메일 비밀번호')).toHaveTextContent(
        '이메일 비밀번호를 입력하세요'
      );
    });

    it('validates IMAP server in auto mode - empty', () => {
      const noImapForm = { ...secudiumForm, imap_server: '' };
      render(<CredentialEditModal {...secudiumProps} credentialForm={noImapForm} />);
      expect(screen.getByTestId('error-IMAP 서버')).toHaveTextContent('IMAP 서버를 입력하세요');
    });

    it('validates IMAP server in auto mode - invalid hostname', () => {
      const badImapForm = { ...secudiumForm, imap_server: 'not a hostname!' };
      render(<CredentialEditModal {...secudiumProps} credentialForm={badImapForm} />);
      expect(screen.getByTestId('error-IMAP 서버')).toHaveTextContent(
        '올바른 호스트명 형식이 아닙니다'
      );
    });

    it('does not validate email fields in manual mode', () => {
      const manualForm = {
        ...secudiumForm,
        otp_mode: 'manual' as const,
        email: '',
        email_password: '',
        imap_server: '',
      };
      render(<CredentialEditModal {...secudiumProps} credentialForm={manualForm} />);
      expect(screen.getByText('저장')).not.toBeDisabled();
    });

    it('does not show SECUDIUM fields for non-SECUDIUM service', () => {
      render(<CredentialEditModal {...defaultProps} />);
      expect(screen.queryByText('자동 (이메일 OTP)')).not.toBeInTheDocument();
      expect(screen.queryByText('수동 (직접 입력)')).not.toBeInTheDocument();
    });
  });
});
