'use client';

import { useMemo, useCallback, useRef } from 'react';
import Modal from '@/components/ui/Modal';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import { CredentialFormState, SecudiumCredentialFormState, OtpMode } from './types';

interface CredentialEditModalProps {
  show: boolean;
  onClose: () => void;
  editingService: string | null;
  credentialForm: CredentialFormState | SecudiumCredentialFormState;
  onFormChange: (form: CredentialFormState | SecudiumCredentialFormState) => void;
  onSave: () => void;
  loading?: boolean;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const HOSTNAME_REGEX =
  /^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$/;

interface ValidationErrors {
  email?: string;
  email_password?: string;
  imap_server?: string;
  username?: string;
}

export function CredentialEditModal({
  show,
  onClose,
  editingService,
  credentialForm,
  onFormChange,
  onSave,
  loading = false,
}: CredentialEditModalProps) {
  const isSecudium = editingService === 'SECUDIUM';
  const secudiumForm = isSecudium ? (credentialForm as SecudiumCredentialFormState) : null;
  const savingRef = useRef(false);

  const handleOtpModeChange = (mode: OtpMode) => {
    if (secudiumForm) {
      onFormChange({ ...secudiumForm, otp_mode: mode });
    }
  };

  const errors = useMemo<ValidationErrors>(() => {
    const errs: ValidationErrors = {};

    if (!credentialForm.username.trim()) {
      errs.username = '사용자명을 입력하세요';
    }

    if (isSecudium && secudiumForm?.otp_mode === 'auto') {
      const email = secudiumForm.email?.trim() || '';
      if (!email) {
        errs.email = '이메일을 입력하세요';
      } else if (!EMAIL_REGEX.test(email)) {
        errs.email = '올바른 이메일 형식이 아닙니다';
      }

      if (!secudiumForm.email_password?.trim()) {
        errs.email_password = '이메일 비밀번호를 입력하세요';
      }

      const imapServer = secudiumForm.imap_server?.trim() || '';
      if (!imapServer) {
        errs.imap_server = 'IMAP 서버를 입력하세요';
      } else if (!HOSTNAME_REGEX.test(imapServer)) {
        errs.imap_server = '올바른 호스트명 형식이 아닙니다 (예: imap.kakao.com)';
      }
    }

    return errs;
  }, [credentialForm, isSecudium, secudiumForm]);

  const isValid = Object.keys(errors).length === 0;

  const handleSave = useCallback(() => {
    if (loading || savingRef.current || !isValid) return;
    savingRef.current = true;
    onSave();
    setTimeout(() => {
      savingRef.current = false;
    }, 1000);
  }, [loading, isValid, onSave]);

  return (
    <Modal isOpen={show} onClose={onClose} title={`${editingService} 인증정보 수정`} size="md">
      <div className="space-y-4">
        {isSecudium && secudiumForm && (
          <div className="space-y-4 border-b border-gray-700 pb-4 mb-4">
            <span className="block text-sm font-medium text-gray-300 mb-2">OTP 인증 방식</span>
            <div className="flex space-x-2 mb-4">
              <button
                type="button"
                onClick={() => handleOtpModeChange('auto')}
                className={`flex-1 py-2 px-4 rounded-full text-sm font-medium transition-colors ${
                  secudiumForm.otp_mode === 'auto'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                자동 (이메일 OTP)
              </button>
              <button
                type="button"
                onClick={() => handleOtpModeChange('manual')}
                className={`flex-1 py-2 px-4 rounded-full text-sm font-medium transition-colors ${
                  secudiumForm.otp_mode === 'manual'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                수동 (직접 입력)
              </button>
            </div>

            {secudiumForm.otp_mode === 'auto' ? (
              <div className="p-4 border border-gray-700 rounded-lg space-y-3 bg-gray-800/50">
                <Input
                  label="이메일 (카카오 계정)"
                  required
                  value={secudiumForm.email || ''}
                  onChange={(e) => onFormChange({ ...secudiumForm, email: e.target.value })}
                  placeholder="example@kakao.com"
                  error={errors.email}
                />
                <Input
                  label="이메일 비밀번호"
                  type="password"
                  required
                  value={secudiumForm.email_password || ''}
                  onChange={(e) =>
                    onFormChange({ ...secudiumForm, email_password: e.target.value })
                  }
                  placeholder="이메일 비밀번호"
                  error={errors.email_password}
                />
                <Input
                  label="IMAP 서버"
                  required
                  value={secudiumForm.imap_server || 'imap.kakao.com'}
                  onChange={(e) => onFormChange({ ...secudiumForm, imap_server: e.target.value })}
                  placeholder="imap.kakao.com"
                  error={errors.imap_server}
                />
              </div>
            ) : (
              <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg text-blue-200 text-sm">
                연결 테스트 시 카카오톡으로 받은 OTP 번호를 직접 입력합니다.
              </div>
            )}
          </div>
        )}

        <Input
          label="사용자명"
          required
          value={credentialForm.username}
          onChange={(e) => onFormChange({ ...credentialForm, username: e.target.value })}
          placeholder="사용자명"
          error={errors.username}
        />
        <Input
          label="비밀번호"
          type="password"
          value={credentialForm.password}
          onChange={(e) => onFormChange({ ...credentialForm, password: e.target.value })}
          placeholder="변경하지 않으려면 비워두세요"
        />
        <Input
          label="수집 주기 (초)"
          type="number"
          value={credentialForm.collection_interval}
          onChange={(e) =>
            onFormChange({
              ...credentialForm,
              collection_interval: e.target.value,
            })
          }
          placeholder="3600"
        />
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="enabled"
            checked={credentialForm.enabled}
            onChange={(e) => onFormChange({ ...credentialForm, enabled: e.target.checked })}
            className="h-4 w-4 rounded border-gray-300"
          />
          <label htmlFor="enabled" className="text-sm text-gray-700">
            활성화
          </label>
        </div>
        <div className="flex justify-end space-x-2 pt-4">
          <Button variant="secondary" onClick={onClose}>
            취소
          </Button>
          <Button onClick={handleSave} loading={loading} disabled={!isValid || loading}>
            저장
          </Button>
        </div>
      </div>
    </Modal>
  );
}
