'use client';

import { useState, useRef, useEffect } from 'react';
import Modal from '@/components/ui/Modal';
import Button from '@/components/ui/Button';

interface OtpInputDialogProps {
  show: boolean;
  onClose: () => void;
  onSubmit: (otpCode: string) => void;
  loading?: boolean;
  serviceName: string;
}

export default function OtpInputDialog({
  show,
  onClose,
  onSubmit,
  loading = false,
  serviceName,
}: OtpInputDialogProps) {
  const [otpCode, setOtpCode] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (show && inputRef.current) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [show]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (otpCode.length === 6) {
      onSubmit(otpCode);
    }
  };

  return (
    <Modal isOpen={show} onClose={onClose} title="OTP 인증" size="sm">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="text-center space-y-2">
          <p className="text-gray-300">OTP를 입력해주세요.</p>
        </div>

        <div className="flex justify-center">
          <input
            ref={inputRef}
            type="text"
            maxLength={6}
            value={otpCode}
            onChange={(e) => setOtpCode(e.target.value.replace(/[^0-9]/g, ''))}
            className="w-48 text-center text-3xl font-mono tracking-widest bg-gray-900 border border-gray-600 rounded-lg p-3 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all placeholder-gray-700"
            placeholder="000000"
            disabled={loading}
          />
        </div>

        <div className="flex justify-end space-x-2 pt-2">
          <Button variant="secondary" onClick={onClose} disabled={loading} type="button">
            취소
          </Button>
          <Button type="submit" loading={loading} disabled={otpCode.length !== 6}>
            확인
          </Button>
        </div>
      </form>
    </Modal>
  );
}
