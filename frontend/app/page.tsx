'use client';

import {
  Database,
  Shield,
  PlusCircle,
  Clock,
  Activity,
  TrendingUp,
  Globe,
  History,
  Table2,
  CheckCircle,
  AlertTriangle,
  Loader2,
  BarChart3,
} from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import {
  getStats,
  getSystemStatus,
  getCollectionHistory,
  getCollectionStatus,
  getWhitelist,
} from '@/lib/api';
import { DashboardStats, SystemStatus, ActivityLog } from '@/types';

interface CollectionStatus {
  is_running: boolean;
  collectors: Record<
    string,
    {
      enabled: boolean;
      error_count: number;
      interval_seconds: number;
      last_run: string | null;
      next_run: string | null;
      run_count: number;
    }
  >;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [recentActivity, setRecentActivity] = useState<ActivityLog[]>([]);
  const [collectionStatus, setCollectionStatus] = useState<CollectionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const isCollectionStatusRequestInFlight = useRef(false);

  useEffect(() => {
    fetchStats();
    fetchSystemStatus();
    fetchRecentActivity();
    fetchCollectionStatus();

    const interval = setInterval(() => {
      fetchStats();
      fetchSystemStatus();
      fetchRecentActivity();
    }, 30000);

    const collectionInterval = setInterval(fetchCollectionStatus, 5000);

    return () => {
      clearInterval(interval);
      clearInterval(collectionInterval);
    };
  }, []);

  const fetchStats = async () => {
    try {
      const [statsData, whitelistData] = await Promise.all([getStats(), getWhitelist()]);

      let totalIps = 0;
      let activeIps = 0;
      let recentAdditions = 0;
      let lastUpdate = null;
      let whitelistedIps = 0;

      if (statsData) {
        // /api/web-stats returns { success, stats: { total_ips, active_ips, ... }, last_updated }
        const data = statsData.stats || statsData.data || {};

        // Ensure numbers are numbers
        totalIps = Number(data.total_ips) || 0;
        activeIps = Number(data.active_ips) || 0;
        recentAdditions = Number(data.recent_additions) || Number(data.new_today) || 0;
        lastUpdate = data.last_update || statsData.last_updated || null;
      }

      if (whitelistData) {
        // Handle different pagination structures
        whitelistedIps =
          Number(whitelistData.data?.pagination?.total) ||
          Number(whitelistData.data?.items?.length) ||
          0;
      }

      setStats({
        total_ips: totalIps,
        active_ips: activeIps,
        recent_additions: recentAdditions,
        whitelisted_ips: whitelistedIps,
        last_update: lastUpdate,
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSystemStatus = async () => {
    try {
      const response = await getSystemStatus();
      if (response) {
        const data = response;

        // API returns flat: { status, database_connected, ... }
        const status: SystemStatus = {
          service: {
            status:
              data.service?.status === 'healthy' || data.status === 'healthy'
                ? 'healthy'
                : 'unhealthy',
          },
          components: {
            database: {
              status:
                data.components?.database?.status === 'healthy' || data.database_connected === true
                  ? 'healthy'
                  : 'unhealthy',
            },
          },
          collection: {
            collection_enabled: data.collection?.collection_enabled ?? true,
          },
        };
        setSystemStatus(status);
      }
    } catch (error) {
      console.error('Failed to fetch system status:', error);
    }
  };

  const fetchRecentActivity = async () => {
    try {
      const response = await getCollectionHistory();
      if (response) {
        const history = Array.isArray(response.data) ? response.data : response.data?.history || [];
        setRecentActivity(history);
      }
    } catch (error) {
      console.error('Failed to fetch recent activity:', error);
    }
  };

  const fetchCollectionStatus = async () => {
    if (isCollectionStatusRequestInFlight.current) return;

    isCollectionStatusRequestInFlight.current = true;
    try {
      const response = await getCollectionStatus();
      if (response && response.success && response.data) {
        setCollectionStatus(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch collection status:', error);
    } finally {
      isCollectionStatusRequestInFlight.current = false;
    }
  };

  const statCards = [
    {
      title: '전체 IP 주소',
      value: stats?.total_ips || 0,
      icon: Database,
      gradient: 'from-blue-500 to-blue-600',
      bgGradient: 'from-blue-50 to-blue-100',
      iconBg: 'bg-blue-500',
    },
    {
      title: '차단된 IP',
      value: stats?.active_ips || 0,
      icon: Shield,
      gradient: 'from-red-500 to-red-600',
      bgGradient: 'from-red-50 to-red-100',
      iconBg: 'bg-red-500',
    },
    {
      title: '24시간 신규',
      value: stats?.recent_additions || 0,
      icon: PlusCircle,
      gradient: 'from-green-500 to-green-600',
      bgGradient: 'from-green-50 to-green-100',
      iconBg: 'bg-green-500',
    },
    {
      title: '화이트리스트',
      value: stats?.whitelisted_ips || 0,
      icon: Globe,
      gradient: 'from-purple-500 to-purple-600',
      bgGradient: 'from-purple-50 to-purple-100',
      iconBg: 'bg-purple-500',
    },
  ];

  const quickActions = [
    {
      href: '/ip-management',
      title: 'IP 관리',
      description: '블랙리스트/화이트리스트 관리',
      icon: Shield,
      gradient: 'from-blue-500 to-cyan-500',
      iconBg: 'bg-gradient-to-br from-blue-500 to-cyan-500',
    },
    {
      href: '/collection',
      title: '데이터 수집',
      description: '수집 관리 및 이력',
      icon: History,
      gradient: 'from-green-500 to-emerald-500',
      iconBg: 'bg-gradient-to-br from-green-500 to-emerald-500',
    },
    {
      href: '/analytics',
      title: '일별 통계',
      description: '탐지일 기준 분석',
      icon: BarChart3,
      gradient: 'from-indigo-500 to-purple-500',
      iconBg: 'bg-gradient-to-br from-indigo-500 to-purple-500',
    },
    {
      href: '/fortinet',
      title: 'FortiGate 연동',
      description: '방화벽 블랙리스트 연동',
      icon: Activity,
      gradient: 'from-orange-500 to-red-500',
      iconBg: 'bg-gradient-to-br from-orange-500 to-red-500',
    },
    {
      href: '/database',
      title: '데이터베이스',
      description: '테이블 현황 및 브라우저',
      icon: Table2,
      gradient: 'from-purple-500 to-pink-500',
      iconBg: 'bg-gradient-to-br from-purple-500 to-pink-500',
    },
  ];

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {collectionStatus?.is_running && (
        <div className="mb-6 bg-gradient-to-r from-green-500 via-emerald-500 to-teal-500 rounded-xl p-4 shadow-lg animate-pulse">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="relative">
                <Loader2 className="h-6 w-6 text-white animate-spin" />
                <div className="absolute inset-0 h-6 w-6 bg-white/30 rounded-full animate-ping" />
              </div>
              <div>
                <p className="text-white font-bold text-lg">데이터 수집 진행 중</p>
                <p className="text-green-100 text-sm">
                  {Object.entries(collectionStatus.collectors || {})
                    .filter(([, c]) => c.enabled)
                    .map(([name]) => name)
                    .join(', ')}{' '}
                  수집기 동작 중
                </p>
              </div>
            </div>
            <Link
              href="/collection"
              className="bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
            >
              상세 보기
            </Link>
          </div>
        </div>
      )}

      <div className="mb-8">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 bg-clip-text text-transparent mb-3">
          대시보드
        </h1>
        <p className="text-gray-600 text-lg">실시간 IP 블랙리스트 모니터링 및 관리</p>
      </div>

      {/* Stats Cards with Modern Design */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-xl p-6 shadow-lg animate-pulse">
              <div className="h-12 bg-gray-200 rounded mb-4"></div>
              <div className="h-8 bg-gray-200 rounded mb-2"></div>
              <div className="h-4 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {statCards.map((card, index) => (
            <div key={index} className="relative overflow-hidden rounded-xl bg-white shadow-lg">
              <div className="relative p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className={`${card.iconBg} p-3 rounded-lg text-white shadow-lg`}>
                    <card.icon className="h-6 w-6" />
                  </div>
                </div>
                <h3 className="text-3xl font-bold text-gray-900 mb-1">
                  {card.value.toLocaleString()}
                </h3>
                <p className="text-gray-600 text-sm font-medium">{card.title}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Last Update Info */}
      <div className="bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl p-4 mb-8 border border-gray-200">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <Clock className="h-5 w-5 text-gray-600" />
            <span className="whitespace-nowrap text-sm text-gray-600 font-medium">
              마지막 업데이트:
            </span>
            <span className="text-sm font-semibold text-gray-900">
              {stats?.last_update ? new Date(stats.last_update).toLocaleString('ko-KR') : 'N/A'}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-green-600 font-medium">실시간 동기화</span>
          </div>
        </div>
      </div>

      {/* Quick Actions with Modern Cards */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">빠른 작업</h2>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {quickActions.map((action, index) => (
            <Link
              key={index}
              href={action.href}
              className="group relative bg-white rounded-xl p-6 shadow-lg hover:shadow-2xl transition-all duration-300 hover:-translate-y-2 overflow-hidden"
            >
              {/* Gradient overlay on hover */}
              <div
                className={`absolute inset-0 bg-gradient-to-br ${action.gradient} opacity-0 group-hover:opacity-10 transition-opacity duration-300`}
              ></div>

              <div className="relative flex min-w-0 items-center space-x-4">
                <div
                  className={`${action.iconBg} p-4 rounded-xl text-white shadow-lg transform group-hover:scale-110 group-hover:rotate-3 transition-all duration-300`}
                >
                  <action.icon className="h-8 w-8" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="break-keep font-bold text-gray-900 text-lg mb-1 group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-blue-600 group-hover:to-purple-600 transition-all duration-300">
                    {action.title}
                  </h3>
                  <p className="break-keep text-sm text-gray-600 group-hover:text-gray-700 transition-colors duration-300">
                    {action.description}
                  </p>
                </div>
                <div className="absolute right-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
                  <svg
                    className="w-6 h-6 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* System Status Section */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">시스템 상태</h2>
        {systemStatus ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div
              className={`flex items-center space-x-4 p-4 rounded-lg border ${
                systemStatus.service?.status === 'healthy'
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}
            >
              <div
                className={`p-3 rounded-lg ${
                  systemStatus.service?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                }`}
              >
                <Activity className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-sm text-gray-600 font-medium">API 서버</p>
                <p
                  className={`text-lg font-bold ${
                    systemStatus.service?.status === 'healthy' ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {systemStatus.service?.status === 'healthy' ? '정상' : '오류'}
                </p>
              </div>
            </div>
            <div
              className={`flex items-center space-x-4 p-4 rounded-lg border ${
                systemStatus.components?.database?.status === 'healthy'
                  ? 'bg-blue-50 border-blue-200'
                  : 'bg-red-50 border-red-200'
              }`}
            >
              <div
                className={`p-3 rounded-lg ${
                  systemStatus.components?.database?.status === 'healthy'
                    ? 'bg-blue-500'
                    : 'bg-red-500'
                }`}
              >
                <Database className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-sm text-gray-600 font-medium">데이터베이스</p>
                <p
                  className={`text-lg font-bold ${
                    systemStatus.components?.database?.status === 'healthy'
                      ? 'text-blue-600'
                      : 'text-red-600'
                  }`}
                >
                  {systemStatus.components?.database?.status === 'healthy' ? '정상' : '오류'}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4 p-4 bg-purple-50 rounded-lg border border-purple-200">
              <div className="bg-purple-500 p-3 rounded-lg">
                <TrendingUp className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-sm text-gray-600 font-medium">수집 활성화</p>
                <p className="text-lg font-bold text-purple-600">
                  {collectionStatus
                    ? Object.values(collectionStatus.collectors || {}).some((c) => c.enabled)
                      ? '활성'
                      : '비활성'
                    : systemStatus.collection?.collection_enabled
                      ? '활성'
                      : '비활성'}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg border border-gray-200 animate-pulse"
              >
                <div className="bg-gray-300 p-3 rounded-lg h-12 w-12"></div>
                <div className="flex-1">
                  <div className="h-4 bg-gray-300 rounded mb-2"></div>
                  <div className="h-6 bg-gray-300 rounded"></div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Collection Activity Section */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900">최근 수집 활동</h2>
          <Link
            href="/collection"
            className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
          >
            전체 보기
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
        {recentActivity.length > 0 ? (
          <div className="space-y-3">
            {recentActivity.map((log: ActivityLog, index: number) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
              >
                <div className="flex items-center space-x-4 flex-1 min-w-0">
                  {log.success ? (
                    <div className="p-2 bg-green-100 rounded-lg">
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    </div>
                  ) : (
                    <div className="p-2 bg-red-100 rounded-lg">
                      <AlertTriangle className="h-5 w-5 text-red-600" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 truncate">
                      {log.service_name || 'N/A'}
                    </p>
                    <p className="text-sm text-gray-600 truncate">
                      {log.items_collected || 0}개 수집
                      {log.error_message && ` - ${log.error_message}`}
                    </p>
                  </div>
                </div>
                <div className="text-right ml-4">
                  <p className="text-sm text-gray-500 whitespace-nowrap">
                    {log.collection_date
                      ? new Date(log.collection_date).toLocaleString('ko-KR')
                      : 'N/A'}
                  </p>
                  <p
                    className={`text-xs font-medium ${log.success ? 'text-green-600' : 'text-red-600'}`}
                  >
                    {log.success ? '성공' : '실패'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <History className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p>최근 수집 활동이 없습니다</p>
          </div>
        )}
      </div>
    </main>
  );
}
