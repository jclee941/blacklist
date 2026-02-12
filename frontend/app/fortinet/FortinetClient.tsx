'use client';

import { useState, useEffect } from 'react';
import { Download, RefreshCw, AlertCircle, CheckCircle, Activity } from 'lucide-react';
import { getFortinetPullLogs, getFortinetBlocklist } from '@/lib/api';

interface PullLog {
  id: number;
  device_ip: string;
  user_agent?: string;
  endpoint?: string;
  ip_count?: number;
  response_time_ms?: number;
  status_code?: number;
  created_at?: string;
}

interface PullLogStats {
  total_pulls: number;
  successful_pulls: number;
  failed_pulls: number;
  unique_devices: number;
}

export default function FortinetClient() {
  const [pullLogs, setPullLogs] = useState<PullLog[]>([]);
  const [pullLogStats, setPullLogStats] = useState<PullLogStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [externalConnectorBase, setExternalConnectorBase] = useState('');

  useEffect(() => {
    setExternalConnectorBase(window.location.origin);
  }, []);

  const formatExternalEndpoint = (path: string) =>
    externalConnectorBase ? `${externalConnectorBase}${path}` : path;

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getFortinetPullLogs('limit=50&hours=720');

      if (data.success) {
        setPullLogs(data.data || []);
        setPullLogStats(data.stats || null);
      } else {
        setError(data.error || '데이터를 불러올 수 없습니다');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const downloadBlocklist = async () => {
    try {
      const response = await getFortinetBlocklist();

      if (!response) {
        throw new Error('API 요청 실패');
      }

      let blocklistText = '';

      const data = response.data;

      if (typeof data === 'object' && data !== null) {
        // Handle JSON response: {success:true, data:{blocklist:"...", total:N}}
        if (
          'success' in data &&
          data.success &&
          data.data?.blocklist &&
          typeof data.data.blocklist === 'string'
        ) {
          blocklistText = data.data.blocklist;
        } else if (
          'success' in data &&
          data.success &&
          'blocklist' in data &&
          typeof data.blocklist === 'string'
        ) {
          blocklistText = data.blocklist;
        } else if ('error' in data && typeof data.error === 'string') {
          throw new Error(data.error || '블랙리스트 다운로드 실패');
        } else {
          throw new Error('블랙리스트 다운로드 실패');
        }
      } else if (typeof data === 'string') {
        // Handle plain text response
        blocklistText = data;
      } else {
        throw new Error('블랙리스트 다운로드 실패');
      }

      if (!blocklistText) {
        throw new Error('블랙리스트 데이터가 비어 있습니다');
      }

      const blob = new Blob([blocklistText], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `fortinet-blocklist-${new Date().toISOString().split('T')[0]}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : '다운로드 중 오류 발생');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-3 text-gray-600">데이터 로딩 중...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center">
          <AlertCircle className="h-6 w-6 text-red-500 mr-3" />
          <div>
            <h3 className="text-red-800 font-semibold">오류 발생</h3>
            <p className="text-red-600 text-sm mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      {pullLogStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-gray-600 text-xs">전체 요청</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {pullLogStats.total_pulls.toLocaleString()}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-gray-600 text-xs">성공</p>
            <p className="text-2xl font-bold text-green-600 mt-1">
              {pullLogStats.successful_pulls.toLocaleString()}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-gray-600 text-xs">실패</p>
            <p className="text-2xl font-bold text-red-600 mt-1">
              {pullLogStats.failed_pulls.toLocaleString()}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-gray-600 text-xs">고유 장치</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">
              {pullLogStats.unique_devices.toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h3 className="text-lg font-semibold text-gray-900">FortiGate 블랙리스트 관리</h3>
          <div className="flex gap-3">
            <button
              onClick={fetchData}
              className="flex items-center px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              새로고침
            </button>
            <button
              onClick={downloadBlocklist}
              className="flex items-center px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition"
            >
              <Download className="h-4 w-4 mr-2" />
              블랙리스트 다운로드
            </button>
          </div>
        </div>

        <div className="mt-4 p-4 bg-blue-50 rounded-lg">
          <h4 className="font-medium text-blue-900 mb-2">FortiGate External Connector</h4>
          <p className="text-xs text-blue-800 mb-3">
            FortiGate External Resource 설정에서 아래 URL을 사용합니다.
          </p>
          <div className="text-sm">
            <span className="font-mono bg-white px-2 py-1 rounded text-blue-700">
              GET {formatExternalEndpoint('/api/fortinet/blocklist')}
            </span>
            <span className="text-gray-600 ml-2">- FortiGate External Connector 블랙리스트</span>
          </div>
        </div>
      </div>

      {/* Pull Logs Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            <Activity className="h-5 w-5 inline mr-2" />
            FortiGate 요청 기록 (최근 30일)
          </h3>
        </div>

        {pullLogs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    장치 IP
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    엔드포인트
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    IP 개수
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    응답시간
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    상태
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    요청시각
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    User Agent
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {pullLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="font-mono text-sm text-gray-900">{log.device_ip}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-600">{log.endpoint || '-'}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {log.ip_count?.toLocaleString() || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {log.response_time_ms ? `${log.response_time_ms}ms` : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {log.status_code === 200 ? (
                        <span className="inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          성공
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                          <AlertCircle className="h-3 w-3 mr-1" />
                          실패
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {log.created_at ? new Date(log.created_at).toLocaleString('ko-KR') : '-'}
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-600 line-clamp-1">
                        {log.user_agent || '-'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-6 py-12 text-center text-gray-500">요청 기록이 없습니다</div>
        )}
      </div>
    </div>
  );
}
