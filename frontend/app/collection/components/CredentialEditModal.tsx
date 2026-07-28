'use client';

import { useMemo, useCallback, useEffect, useRef, useState } from 'react';
import Modal from '@/components/ui/Modal';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import { COLLECTION_INTERVAL_OPTIONS } from '@/types';
import { CredentialFormState } from './types';

const COLLECTION_INTERVAL_LABELS = {
  hourly: '매시간',
  daily: '매일',
  weekly: '매주',
};

interface CredentialEditModalProps {
  show: boolean;
  onClose: () => void;
  editingService: string | null;
  configured: boolean;
  credentialForm: CredentialFormState;
  onFormChange: (form: CredentialFormState) => void;
  onSave: () => void;
  loading?: boolean;
}

interface ValidationErrors {
  username?: string;
  password?: string;
}

export function CredentialEditModal({
  show,
  onClose,
  editingService,
  configured,
  credentialForm,
  onFormChange,
  onSave,
  loading = false,
}: CredentialEditModalProps) {
  const savingRef = useRef(false);
  const [hasAttemptedSave, setHasAttemptedSave] = useState(false);

  useEffect(() => {
    if (!show) {
      savingRef.current = false;
      setHasAttemptedSave(false);
    }
  }, [show]);

  const errors = useMemo<ValidationErrors>(() => {
    const errs: ValidationErrors = {};

    if (!credentialForm.username.trim()) {
      errs.username = '사용자명을 입력하세요';
    }
    if (!configured && !credentialForm.password.trim()) {
      errs.password = '비밀번호를 입력하세요';
    }

    return errs;
  }, [configured, credentialForm]);

  const isValid = Object.keys(errors).length === 0;

  const handleSave = useCallback(() => {
    if (loading || savingRef.current) return;
    if (!isValid) {
      setHasAttemptedSave(true);
      return;
    }

    setHasAttemptedSave(false);
    savingRef.current = true;
    onSave();
    setTimeout(() => {
      savingRef.current = false;
    }, 1000);
  }, [loading, isValid, onSave]);

  const handleClose = useCallback(() => {
    savingRef.current = false;
    setHasAttemptedSave(false);
    onClose();
  }, [onClose]);

  return (
    <Modal isOpen={show} onClose={handleClose} title={`${editingService} 설정 및 저장`} size="md">
      <div className="space-y-4">
        <Input
          label="사용자명"
          required
          value={credentialForm.username}
          onChange={(e) => onFormChange({ ...credentialForm, username: e.target.value })}
          placeholder="사용자명"
          error={hasAttemptedSave ? errors.username : undefined}
        />
        <Input
          label="비밀번호"
          type="password"
          required={!configured}
          value={credentialForm.password}
          onChange={(e) => onFormChange({ ...credentialForm, password: e.target.value })}
          placeholder={configured ? '변경하지 않으려면 비워두세요' : '비밀번호'}
          error={hasAttemptedSave ? errors.password : undefined}
        />
        <div>
          <label
            htmlFor="collection-interval"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            수집 주기
          </label>
          <select
            id="collection-interval"
            value={credentialForm.collection_interval}
            onChange={(e) =>
              onFormChange({
                ...credentialForm,
                collection_interval:
                  e.target.value === 'hourly'
                    ? 'hourly'
                    : e.target.value === 'weekly'
                      ? 'weekly'
                      : 'daily',
              })
            }
            className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
          >
            {COLLECTION_INTERVAL_OPTIONS.map((interval) => (
              <option key={interval} value={interval}>
                {COLLECTION_INTERVAL_LABELS[interval]}
              </option>
            ))}
          </select>
        </div>
        <label htmlFor="enabled" className="flex min-h-11 cursor-pointer items-center space-x-2">
          <input
            type="checkbox"
            id="enabled"
            checked={credentialForm.enabled}
            onChange={(e) => onFormChange({ ...credentialForm, enabled: e.target.checked })}
            className="h-4 w-4 rounded border-gray-300"
          />
          <span className="text-sm text-gray-700">활성화</span>
        </label>
        <div className="flex justify-end space-x-2 pt-4">
          <Button className="min-h-11" variant="secondary" onClick={handleClose}>
            취소
          </Button>
          <Button className="min-h-11" onClick={handleSave} loading={loading} disabled={loading}>
            설정 및 저장
          </Button>
        </div>
      </div>
    </Modal>
  );
}
