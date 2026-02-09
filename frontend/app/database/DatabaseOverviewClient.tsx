'use client';

import { useState, useEffect } from 'react';
import { Database, Table2, RefreshCw } from 'lucide-react';
import { getDatabaseTables, getSystemStatus } from '@/lib/api';

interface SchemaTable {
  name: string;
  column_count: number;
  row_count: number;
}

interface DbConnection {
  host: string;
  port: string;
  database: string;
  status: string;
}

export default function DatabaseOverviewClient() {
  const [tables, setTables] = useState<SchemaTable[]>([]);
  const [dbInfo, setDbInfo] = useState<DbConnection>({
    host: '-',
    port: '-',
    database: '-',
    status: 'unknown',
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSchema = async () => {
    setLoading(true);
    setError(null);
    try {
      const [payload, connStatus] = await Promise.all([
        getDatabaseTables(),
        getSystemStatus().catch(() => null),
      ]);

      if (connStatus) {
        setDbInfo({
          host: connStatus.host || '-',
          port: connStatus.port || '-',
          database: connStatus.database || '-',
          status: connStatus.status || 'unknown',
        });
      }

      if (!payload || !payload.success || !payload.tables) {
        setError('테이블 데이터가 올바르지 않습니다.');
        return;
      }

      const tablesData = Object.entries(
        (payload.tables || {}) as Record<string, { columns: unknown[]; record_count: number }>
      ).map(([name, info]) => ({
        name,
        column_count: info.columns?.length || 0,
        row_count: info.record_count || -1,
      }));

      setTables(tablesData);
    } catch (err) {
      console.error('Failed to fetch schema:', err);
      setError('테이블 현황을 불러오지 못했습니다.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchema();
  }, []);

  const totalRows = tables.reduce(
    (sum, table) => sum + (table.row_count > 0 ? table.row_count : 0),
    0
  );
  const pendingRows = tables.filter((table) => table.row_count < 0).length;

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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Table2 className="h-5 w-5 text-blue-600" />
            테이블 현황
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            총 {tables.length.toLocaleString()}개 테이블, 합계 {totalRows.toLocaleString()}행
            {pendingRows > 0 && ` (집계중 ${pendingRows.toLocaleString()}개)`}
          </p>
        </div>
        <button
          onClick={fetchSchema}
          className="flex items-center px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          새로고침
        </button>
      </div>

      {error ? (
        <div className="bg-white rounded-lg shadow p-6 text-sm text-red-600">{error}</div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    테이블
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    컬럼 수
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    행 수
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {tables.length > 0 ? (
                  tables.map((table) => {
                    const rowCount =
                      table.row_count >= 0 ? table.row_count.toLocaleString() : '집계중';
                    const columnCount =
                      typeof table.column_count === 'number'
                        ? table.column_count.toLocaleString()
                        : '-';

                    return (
                      <tr key={table.name} className="hover:bg-gray-50 transition">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {table.name}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700">{columnCount}</td>
                        <td className="px-4 py-3 text-sm text-gray-700">{rowCount}</td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={3} className="px-4 py-10 text-center text-gray-500">
                      테이블 정보가 없습니다
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
          <Database className="h-6 w-6 mr-2 text-blue-600" />
          데이터베이스 정보
        </h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">데이터베이스</dt>
            <dd className="mt-1 text-sm text-gray-900">PostgreSQL 15</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">호스트</dt>
            <dd className="mt-1 text-sm text-gray-900">
              {dbInfo.host}:{dbInfo.port}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">데이터베이스명</dt>
            <dd className="mt-1 text-sm text-gray-900">{dbInfo.database}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">총 테이블 수</dt>
            <dd className="mt-1 text-sm text-gray-900">{tables.length.toLocaleString()}개</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
