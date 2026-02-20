'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  BarChart3,
  Calendar,
  TrendingUp,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { getDailyDetectionStats } from '@/lib/api';

interface TimelineData {
  detection_day: string;
  ip_count: number;
  source_count: number;
  sources: string;
  first_collected: string;
  last_collected: string;
}

interface AnalyticsResponse {
  success: boolean;
  data: {
    metadata: {
      analysis_period_days: number;
      total_ips: number;
      total_days: number;
      avg_per_day: number;
      generated_at: string;
    };
    timeline: TimelineData[];
    source_statistics: Array<{
      source: string;
      total_ips: number;
      active_days: number;
      first_detection: string;
      last_detection: string;
      avg_per_day: number;
    }>;
  };
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(365);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getDailyDetectionStats(days);
      setData(response);
      setCurrentPage(1);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const timeline = data?.data?.timeline || [];
  const metadata = data?.data?.metadata;
  const sourceStats = data?.data?.source_statistics || [];

  const totalPages = Math.ceil(timeline.length / itemsPerPage);
  const paginatedTimeline = timeline.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const maxCount = Math.max(...timeline.map((d) => d.ip_count), 1);

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 bg-clip-text text-transparent mb-3">
          일별 탐지 통계
        </h1>
        <p className="text-gray-600 text-lg">탐지일 기준 IP 수집 현황 분석</p>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value={30}>최근 30일</option>
            <option value={90}>최근 90일</option>
            <option value={180}>최근 180일</option>
            <option value={365}>최근 1년</option>
            <option value={730}>최근 2년</option>
          </select>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            <span>새로고침</span>
          </button>
        </div>
        {metadata && (
          <div className="text-sm text-gray-500">
            생성: {new Date(metadata.generated_at).toLocaleString('ko-KR')}
          </div>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-xl p-6 shadow-lg animate-pulse">
              <div className="h-12 bg-gray-200 rounded mb-4"></div>
              <div className="h-8 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-xl p-6 shadow-lg">
              <div className="flex items-center space-x-3 mb-2">
                <div className="bg-blue-500 p-2 rounded-lg">
                  <BarChart3 className="h-5 w-5 text-white" />
                </div>
                <span className="text-gray-600 text-sm">총 IP 수</span>
              </div>
              <p className="text-3xl font-bold text-gray-900">
                {metadata?.total_ips?.toLocaleString() || 0}
              </p>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-lg">
              <div className="flex items-center space-x-3 mb-2">
                <div className="bg-green-500 p-2 rounded-lg">
                  <Calendar className="h-5 w-5 text-white" />
                </div>
                <span className="text-gray-600 text-sm">활성 일수</span>
              </div>
              <p className="text-3xl font-bold text-gray-900">{metadata?.total_days || 0}일</p>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-lg">
              <div className="flex items-center space-x-3 mb-2">
                <div className="bg-purple-500 p-2 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-white" />
                </div>
                <span className="text-gray-600 text-sm">일평균</span>
              </div>
              <p className="text-3xl font-bold text-gray-900">
                {metadata?.avg_per_day?.toLocaleString() || 0}
              </p>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4">일별 수집 현황</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">
                      탐지일
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-semibold text-gray-600">
                      IP 수
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">
                      분포
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">
                      소스
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedTimeline.map((item, index) => (
                    <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <span className="font-medium text-gray-900">{item.detection_day}</span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="font-bold text-gray-900">
                          {item.ip_count.toLocaleString()}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="w-full bg-gray-200 rounded-full h-2.5">
                          <div
                            className="h-2.5 rounded-full bg-blue-500"
                            style={{ width: `${(item.ip_count / maxCount) * 100}%` }}
                          ></div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-gray-600">{item.sources}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
                <span className="text-sm text-gray-600">
                  {timeline.length}개 중 {(currentPage - 1) * itemsPerPage + 1}-
                  {Math.min(currentPage * itemsPerPage, timeline.length)}
                </span>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="p-2 rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <span className="text-sm text-gray-600">
                    {currentPage} / {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="p-2 rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {sourceStats.length > 0 && (
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">소스별 통계</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sourceStats.map((source, index) => (
                  <div key={index} className="p-4 bg-gray-50 rounded-lg">
                    <h3 className="font-bold text-gray-900 mb-2">{source.source}</h3>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">총 IP</span>
                        <span className="font-medium">{source.total_ips.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">활성일</span>
                        <span className="font-medium">{source.active_days}일</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">일평균</span>
                        <span className="font-medium">{source.avg_per_day}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </main>
  );
}
