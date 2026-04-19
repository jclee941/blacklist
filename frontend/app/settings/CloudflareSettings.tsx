'use client';

import { useCallback, useEffect, useState } from 'react';
import { Cloud, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import {
  getCloudflareCredentials,
  saveCloudflareCredentials,
  testCloudflareConnection,
} from '@/lib/api';

export default function CloudflareSettings() {
  const [apiToken, setApiToken] = useState('');
  const [accountId, setAccountId] = useState('');
  const [listId, setListId] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'unknown' | 'connected' | 'failed'>(
    'unknown'
  );

  const loadCredentials = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getCloudflareCredentials();
      if (res.success && res.data) {
        const cred = res.data;
        setApiToken(cred.password ? '••••••••' : '');
        setAccountId(cred.config?.account_id || '');
        setListId(cred.config?.list_id || '');
        if (cred.password) {
          setConnectionStatus('connected');
        }
      }
    } catch {
      // No credentials saved yet
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCredentials();
  }, [loadCredentials]);

  const handleSave = async () => {
    if (!apiToken) {
      setMessage({ type: 'error', text: 'API Token을 입력하세요' });
      return;
    }
    if (!accountId || !listId) {
      setMessage({ type: 'error', text: 'Account ID와 List ID를 모두 입력하세요' });
      return;
    }
    try {
      setSaving(true);
      const res = await saveCloudflareCredentials({
        api_token: apiToken,
        account_id: accountId,
        list_id: listId,
      });
      if (res.success) {
        setMessage({ type: 'success', text: res.data?.message || '저장 완료' });
        setApiToken('••••••••');
      } else {
        setMessage({ type: 'error', text: res.data?.message || '저장 실패' });
      }
    } catch (err: unknown) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : '저장 실패' });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    try {
      setTesting(true);
      setMessage(null);
      const res = await testCloudflareConnection();
      if (res.success) {
        setConnectionStatus('connected');
        setMessage({ type: 'success', text: res.data?.message || '연결 성공' });
      } else {
        setConnectionStatus('failed');
        setMessage({ type: 'error', text: res.data?.message || '연결 실패' });
      }
    } catch (err: unknown) {
      setConnectionStatus('failed');
      setMessage({ type: 'error', text: err instanceof Error ? err.message : '연결 실패' });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Cloud className="h-5 w-5 text-orange-500" />
        <div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Cloudflare WAF 연동</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            블랙리스트 IP를 Cloudflare Lists API에 자동 푸시합니다 (Enterprise)
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {connectionStatus === 'connected' && (
            <span className="flex items-center gap-1 text-sm text-green-600">
              <CheckCircle className="h-4 w-4" /> 연결됨
            </span>
          )}
          {connectionStatus === 'failed' && (
            <span className="flex items-center gap-1 text-sm text-red-600">
              <XCircle className="h-4 w-4" /> 연결 실패
            </span>
          )}
        </div>
      </div>

      {message && (
        <div
          className={`rounded-md p-3 text-sm ${
            message.type === 'success'
              ? 'bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-400'
              : 'bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="grid gap-4">
        <div>
          <label
            htmlFor="cloudflare-api-token"
            className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            API Token
          </label>
          <input
            id="cloudflare-api-token"
            type="password"
            value={apiToken}
            onChange={(e) => setApiToken(e.target.value)}
            placeholder="Cloudflare API Token"
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          />
          <p className="mt-1 text-xs text-gray-500">
            dash.cloudflare.com/profile/api-tokens 에서 생성 (Account Filter Lists: Edit 권한)
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="cloudflare-account-id"
              className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Account ID
            </label>
            <input
              id="cloudflare-account-id"
              type="text"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              placeholder="a8d9c67f..."
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-mono text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
            />
          </div>
          <div>
            <label
              htmlFor="cloudflare-list-id"
              className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              List ID
            </label>
            <input
              id="cloudflare-list-id"
              type="text"
              value={listId}
              onChange={(e) => setListId(e.target.value)}
              placeholder="c271cf2e..."
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-mono text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
            />
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
          저장
        </button>
        <button
          type="button"
          onClick={handleTest}
          disabled={testing}
          className="inline-flex items-center rounded-md bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-200 disabled:opacity-50 dark:bg-gray-700 dark:text-gray-300"
        >
          {testing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
          연결 테스트
        </button>
      </div>
    </div>
  );
}
