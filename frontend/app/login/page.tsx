'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import type { FormEvent } from 'react';

import Button from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import Input from '@/components/ui/Input';
import { login } from '@/lib/api';

export default function LoginPage() {
  const { replace } = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage('');
    setIsSubmitting(true);

    try {
      await login(username, password);
      replace('/');
    } catch (error: unknown) {
      if (error instanceof Error) {
        setErrorMessage('아이디 또는 비밀번호를 확인해 주세요.');
        return;
      }
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-[100dvh] bg-gray-100 px-4 py-12 flex items-center justify-center">
      <Card className="w-full max-w-md border border-gray-200" padding="lg">
        <div className="mb-6">
          <p className="text-sm font-medium text-blue-600">Blacklist Management Platform</p>
          <h1 className="mt-2 text-2xl font-bold text-gray-900">관리자 로그인</h1>
          <p className="mt-2 text-sm text-gray-600 break-keep">
            관리 기능을 사용하려면 관리자 계정으로 로그인하세요.
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <Input
            label="관리자 아이디"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
            disabled={isSubmitting}
          />
          <Input
            label="비밀번호"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            disabled={isSubmitting}
          />

          {errorMessage && (
            <p
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              role="alert"
            >
              {errorMessage}
            </p>
          )}

          <Button type="submit" className="w-full" loading={isSubmitting}>
            로그인
          </Button>
        </form>
      </Card>
    </main>
  );
}
