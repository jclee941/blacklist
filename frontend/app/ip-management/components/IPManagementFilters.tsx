'use client';

import { Search, Download, Plus } from 'lucide-react';
import { TabType } from './types';

interface IPManagementFiltersProps {
  activeTab: TabType;
  filterType: string;
  filterSource: string;
  searchIP: string;
  isDownloading: boolean;
  onFilterTypeChange: (value: string) => void;
  onFilterSourceChange: (value: string) => void;
  onSearchIPChange: (value: string) => void;
  onSearch: () => void;
  onReset: () => void;
  onDownload: () => void;
  onAdd: () => void;
}

export function IPManagementFilters({
  activeTab,
  filterType,
  filterSource,
  searchIP,
  isDownloading,
  onFilterTypeChange,
  onFilterSourceChange,
  onSearchIPChange,
  onSearch,
  onReset,
  onDownload,
  onAdd,
}: IPManagementFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      {activeTab === 'unified' && (
        <select
          value={filterType}
          onChange={(e) => onFilterTypeChange(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg"
        >
          <option value="">전체</option>
          <option value="whitelist">화이트리스트만</option>
          <option value="blacklist">블랙리스트만</option>
        </select>
      )}

      {activeTab === 'unified' && (
        <select
          value={filterSource}
          onChange={(e) => onFilterSourceChange(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg"
        >
          <option value="">소스 전체</option>
          <option value="REGTECH">REGTECH</option>
          <option value="MANUAL">수동등록</option>
        </select>
      )}

      <div className="flex items-center gap-2 flex-1 max-w-md">
        <input
          type="text"
          placeholder="IP 주소 검색..."
          value={searchIP}
          onChange={(e) => onSearchIPChange(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg"
        />
        <button
          onClick={onSearch}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
        >
          <Search className="h-5 w-5" />
        </button>
        {searchIP && (
          <button
            onClick={onReset}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"
          >
            초기화
          </button>
        )}
      </div>

      <div className="flex items-center gap-2 ml-auto">
        <button
          onClick={onDownload}
          disabled={isDownloading}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition flex items-center gap-2 disabled:opacity-50"
        >
          <Download className="h-5 w-5" />
          {isDownloading ? '다운로드 중...' : 'Raw Data'}
        </button>

        {activeTab !== 'unified' && (
          <button
            onClick={onAdd}
            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition flex items-center gap-2"
          >
            <Plus className="h-5 w-5" />
            추가
          </button>
        )}
      </div>
    </div>
  );
}
