'use client';

import { useMemo, useCallback, useRef } from 'react';
import Modal from '@/components/ui/Modal';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import { CredentialFormState } from './types';

interface CredentialEditModalProps {
  show: boolean;
  onClose: () => void;
  editingService: string | null;
  credentialForm: CredentialFormState;
  onFormChange: (form: CredentialFormState) => void;
  onSave: () => void;
  loading?: boolean;
}

interface ValidationErrors {
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
  const savingRef = useRef(false);

  const errors = useMemo<ValidationErrors>(() => {
    const errs: ValidationErrors = {};

    if (!credentialForm.username.trim()) {
      errs.username = '사용자명을 입력하세요';
    }

    return errs;
  }, [credentialForm]);

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
