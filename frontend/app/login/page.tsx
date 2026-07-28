'use client';

import { useState } from 'react';
import type { FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { ShieldCheck } from 'lucide-react';
import Button from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import Input from '@/components/ui/Input';
import { login } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const response = await login(username, password);
      if (!response.token) {
        setErrorMessage('로그인에 실패했습니다. 사용자명과 비밀번호를 확인하세요.');
        return;
      }

      router.replace('/');
    } catch (error) {
      if (error instanceof Error) {
        setErrorMessage('로그인에 실패했습니다. 사용자명과 비밀번호를 확인하세요.');
        return;
      }

      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-[100dvh] items-center justify-center bg-gray-50 px-4">
      <Card padding="lg" className="w-full max-w-md">
        <div className="mb-6 text-center">
          <ShieldCheck className="mx-auto mb-3 h-10 w-10 text-blue-500" aria-hidden="true" />
          <h1 className="text-2xl font-bold text-gray-900">관리자 로그인</h1>
          <p className="mt-1 text-sm text-gray-600">Blacklist Management Platform</p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <Input
            label="사용자명"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            required
          />
          <Input
            label="비밀번호"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
          {errorMessage && (
            <p className="text-sm text-red-600" role="alert">
              {errorMessage}
            </p>
          )}
          <Button className="w-full" type="submit" loading={isSubmitting}>
            로그인
          </Button>
        </form>
      </Card>
    </main>
  );
}
