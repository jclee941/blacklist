'use client';

import { Edit2, Trash2, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { IPRecord, TabType } from './types';

interface IPManagementTableProps {
  activeTab: TabType;
  data: IPRecord[];
  loading: boolean;
  page: number;
  total: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onEdit: (record: IPRecord) => void;
  onDelete: (record: IPRecord) => void;
}

export function IPManagementTable({
  activeTab,
  data,
  loading,
  page,
  total,
  totalPages,
  onPageChange,
  onEdit,
  onDelete,
}: IPManagementTableProps) {
  const showBlacklistColumns = activeTab === 'blacklist' || activeTab === 'unified';

  if (loading) {
    return <div className="p-8 text-center text-gray-500">로딩 중...</div>;
  }

  if (data.length === 0) {
    return <div className="p-8 text-center text-gray-500">데이터가 없습니다</div>;
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {activeTab === 'unified' && (
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  구분
                </th>
              )}
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                IP
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                사유
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                소스
              </th>

              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                국가
              </th>
              {showBlacklistColumns && (
                <>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    상태
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    탐지일
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    해제일
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    탐지횟수
                  </th>
                </>
              )}
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                등록일
              </th>
              {activeTab !== 'unified' && (
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  작업
                </th>
              )}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((record) => (
              <tr key={record.id} className="hover:bg-gray-50">
                {activeTab === 'unified' && (
                  <td className="px-4 py-3 text-sm">
                    {record.list_type === 'whitelist' ? (
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                        화이트
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                        블랙
                      </span>
                    )}
                  </td>
                )}
                <td className="px-4 py-3 text-sm font-mono">{record.ip_address}</td>
                <td className="px-4 py-3 text-sm max-w-xs" title={record.reason}>
                  <div className="whitespace-normal break-words">{record.reason}</div>
                </td>
                <td className="px-4 py-3 text-sm">{record.source}</td>

                <td className="px-4 py-3 text-sm">{record.country || '-'}</td>
                {showBlacklistColumns && (
                  <>
                    <td className="px-4 py-3 text-sm">
                      {record.is_active !== undefined &&
                        (record.is_active ? (
                          record.auto_active === false ? (
                            <span
                              className="inline-flex items-center gap-1"
                              title="30일 이상 미탐지"
                            >
                              <AlertTriangle className="h-5 w-5 text-orange-500 inline" />
                              <span className="text-xs text-orange-600">비활동</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1">
                              <CheckCircle className="h-5 w-5 text-green-500 inline" />
                              <span className="text-xs text-green-600">활성</span>
                            </span>
                          )
                        ) : (
                          <span className="inline-flex items-center gap-1">
                            <XCircle className="h-5 w-5 text-gray-400 inline" />
                            <span className="text-xs text-gray-500">해제</span>
                          </span>
                        ))}
                    </td>
                    <td className="px-4 py-3 text-sm whitespace-nowrap">
                      {record.detection_date
                        ? new Date(record.detection_date).toLocaleDateString('ko-KR')
                        : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm whitespace-nowrap">
                      {record.removal_date
                        ? new Date(record.removal_date).toLocaleDateString('ko-KR')
                        : '-'}
                    </td>

                    <td className="px-4 py-3 text-sm text-center">
                      {record.detection_count ?? '-'}
                    </td>
                  </>
                )}
                <td className="px-4 py-3 text-sm whitespace-nowrap">
                  {record.created_at
                    ? new Date(record.created_at).toLocaleDateString('ko-KR')
                    : '-'}
                </td>
                {activeTab !== 'unified' && (
                  <td className="px-4 py-3 text-sm">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => onEdit(record)}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => onDelete(record)}
                        className="text-red-600 hover:text-red-800"
                        aria-label={`${record.ip_address} 삭제`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            총 {total}개 (페이지 {page}/{totalPages})
          </div>
          <div className="flex gap-2">
            {page > 1 && (
              <button
                type="button"
                onClick={() => onPageChange(page - 1)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                이전
              </button>
            )}
            {page < totalPages && (
              <button
                type="button"
                onClick={() => onPageChange(page + 1)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                다음
              </button>
            )}
          </div>
        </div>
      )}
    </>
  );
}
