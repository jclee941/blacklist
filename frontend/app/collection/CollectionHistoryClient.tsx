'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Filter,
  ChevronLeft,
  ChevronRight,
  Database,
  TrendingUp,
  AlertTriangle,
  Calendar,
  Timer,
  FileText,
} from 'lucide-react';

import { getCollectionHistory, getCollectionStatistics } from '@/lib/api';

interface CollectionLog {
  id: number;
  success: boolean;
  service_name: string;
  items_collected: number;
  new_count?: number;
  updated_count?: number;
  collection_date: string;
  duration_seconds?: number;
  error_message?: string;
  metadata?: Record<string, unknown>;
}

interface CollectionStats {
  total_collections: number;
  success_rate: number;
  total_items: number;
  last_collection: string | null;
  avg_duration: number;
}

interface HistoryResponse {
  history: CollectionLog[];
  total: number;
  filtered: number;
}

const ITEMS_PER_PAGE = 20;

export default function CollectionHistoryClient() {
  const [logs, setLogs] = useState<CollectionLog[]>([]);
  const [stats, setStats] = useState<Record<string, CollectionStats>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);

  const fetchCollectionHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Build query params
      const params = new URLSearchParams();
      params.append('limit', String(ITEMS_PER_PAGE));
      if (sourceFilter) params.append('source', sourceFilter);

      const data = await getCollectionHistory(params.toString());
      if (data && data.success && data.data) {
        const historyData = data.data as HistoryResponse;
        let filteredLogs = historyData.history || [];

        // Client-side status filter
        if (statusFilter === 'success') {
          filteredLogs = filteredLogs.filter((log) => log.success);
        } else if (statusFilter === 'failed') {
          filteredLogs = filteredLogs.filter((log) => !log.success);
        }

        setLogs(filteredLogs);
        setTotalItems(historyData.total || 0);
      } else {
        setError('수집 이력을 불러오는데 실패했습니다');
      }

      // Fetch statistics
      const statsData = await getCollectionStatistics();
      if (statsData && statsData.success && statsData.data?.sources) {
        setStats(statsData.data.sources);
      }
    } catch (err) {
      console.error('Failed to fetch collection history:', err);
      setError('네트워크 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  }, [sourceFilter, statusFilter]);

  useEffect(() => {
    fetchCollectionHistory();
  }, [fetchCollectionHistory]);

  const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-';
    if (seconds < 60) return `${seconds.toFixed(1)}초`;
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(0);
    return `${mins}분 ${secs}초`;
  };

  const getServiceColor = (service: string) => {
    switch (service) {
      case 'REGTECH':
        return 'bg-pink-100 text-pink-800 border-pink-200';

      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // Calculate overall stats
  const overallStats = {
    totalCollections: Object.values(stats).reduce((sum, s) => sum + (s.total_collections || 0), 0),
    avgSuccessRate:
      Object.values(stats).length > 0
        ? Object.values(stats).reduce((sum, s) => sum + (s.success_rate || 0), 0) /
          Object.values(stats).length
        : 0,
    totalItems: Object.values(stats).reduce((sum, s) => sum + (s.total_items || 0), 0),
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-3 text-gray-600">데이터 로딩 중...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">총 수집 횟수</p>
              <p className="text-2xl font-bold text-gray-900">{overallStats.totalCollections}</p>
            </div>
            <Database className="h-10 w-10 text-blue-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">평균 성공률</p>
              <p className="text-2xl font-bold text-green-600">
                {overallStats.avgSuccessRate.toFixed(1)}%
              </p>
            </div>
            <TrendingUp className="h-10 w-10 text-green-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">누적 수집량</p>
              <p className="text-2xl font-bold text-purple-600">
                {overallStats.totalItems.toLocaleString()}
              </p>
            </div>
            <FileText className="h-10 w-10 text-purple-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">활성 소스</p>
              <p className="text-2xl font-bold text-orange-600">{Object.keys(stats).length}</p>
            </div>
            <Calendar className="h-10 w-10 text-orange-500" />
          </div>
        </div>
      </div>

      {/* Source Statistics */}
      {Object.keys(stats).length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">소스별 통계</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(stats).map(([source, stat]) => (
              <div
                key={source}
                className={`p-4 rounded-lg border-2 ${
                  source === 'REGTECH' ? 'border-pink-200 bg-pink-50' : 'border-blue-200 bg-blue-50'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span
                    className={`px-3 py-1 rounded-full text-sm font-semibold ${getServiceColor(source)}`}
                  >
                    {source}
                  </span>
                  <span
                    className={`text-sm font-medium ${
                      stat.success_rate >= 90
                        ? 'text-green-600'
                        : stat.success_rate >= 70
                          ? 'text-yellow-600'
                          : 'text-red-600'
                    }`}
                  >
                    성공률 {stat.success_rate?.toFixed(1) || 0}%
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div>
                    <p className="text-gray-500">수집 횟수</p>
                    <p className="font-semibold">{stat.total_collections || 0}회</p>
                  </div>
                  <div>
                    <p className="text-gray-500">누적 수집</p>
                    <p className="font-semibold">{(stat.total_items || 0).toLocaleString()}개</p>
                  </div>
                  <div>
                    <p className="text-gray-500">평균 소요</p>
                    <p className="font-semibold">{formatDuration(stat.avg_duration)}</p>
                  </div>
                </div>
                {stat.last_collection && (
                  <p className="text-xs text-gray-500 mt-2">
                    마지막 수집: {new Date(stat.last_collection).toLocaleString('ko-KR')}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters and Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Filter className="h-5 w-5 text-gray-400" />
            <select
              value={sourceFilter}
              onChange={(e) => {
                setSourceFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
            >
              <option value="">모든 소스</option>
              <option value="REGTECH">REGTECH</option>
            </select>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
          >
            <option value="">모든 상태</option>
            <option value="success">성공</option>
            <option value="failed">실패</option>
          </select>
        </div>

        <button
          onClick={fetchCollectionHistory}
          disabled={loading}
          className="flex items-center px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          새로고침
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center">
          <AlertTriangle className="h-5 w-5 text-red-500 mr-3" />
          <span className="text-red-700">{error}</span>
        </div>
      )}

      {/* History Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  상태
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  서비스
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  수집 개수
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  신규 / 갱신
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  소요 시간
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  수집 시간
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  비고
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {logs.length > 0 ? (
                logs.map((log, index) => (
                  <tr
                    key={log.id || index}
                    className={`hover:bg-gray-50 transition ${!log.success ? 'bg-red-50' : ''}`}
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      {log.success ? (
                        <div className="flex items-center">
                          <CheckCircle className="h-5 w-5 text-green-500" />
                          <span className="ml-2 text-sm text-green-600 font-medium">성공</span>
                        </div>
                      ) : (
                        <div className="flex items-center">
                          <XCircle className="h-5 w-5 text-red-500" />
                          <span className="ml-2 text-sm text-red-600 font-medium">실패</span>
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold border ${getServiceColor(log.service_name)}`}
                      >
                        {log.service_name || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-lg font-semibold text-gray-900">
                        {(log.items_collected || 0).toLocaleString()}
                      </span>
                      <span className="text-sm text-gray-500 ml-1">개</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2 text-sm">
                        <span className="text-green-600 font-medium">
                          신규: {(log.new_count || 0).toLocaleString()}
                        </span>
                        <span className="text-gray-400">/</span>
                        <span className="text-orange-600 font-medium">
                          갱신: {(log.updated_count || 0).toLocaleString()}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center text-gray-600">
                        <Timer className="h-4 w-4 mr-1" />
                        <span>{formatDuration(log.duration_seconds)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                      <div className="flex items-center space-x-2">
                        <Clock className="h-4 w-4" />
                        <span className="text-sm">
                          {log.collection_date
                            ? new Date(log.collection_date).toLocaleString('ko-KR')
                            : 'N/A'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 max-w-xs">
                      {log.error_message ? (
                        <span className="text-red-600 truncate block" title={log.error_message}>
                          {log.error_message}
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center">
                      <Database className="h-12 w-12 text-gray-300 mb-4" />
                      <p className="text-gray-500 text-lg">수집 이력이 없습니다</p>
                      <p className="text-gray-400 text-sm mt-1">
                        데이터 수집이 완료되면 이력이 표시됩니다
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
            <p className="text-sm text-gray-600">
              총 <span className="font-semibold">{totalItems}</span>개 중{' '}
              <span className="font-semibold">
                {(currentPage - 1) * ITEMS_PER_PAGE + 1}-
                {Math.min(currentPage * ITEMS_PER_PAGE, totalItems)}
              </span>
              개 표시
            </p>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="p-2 rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <span className="px-4 py-2 text-sm">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="p-2 rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
