'use client';

import { IPFormData, TabType } from './types';

interface IPManagementFormModalProps {
  isOpen: boolean;
  isEdit: boolean;
  activeTab: TabType;
  listType: 'whitelist' | 'blacklist';
  formData: IPFormData;
  isSubmitting: boolean;
  onFormChange: (data: IPFormData) => void;
  onSubmit: () => void;
  onClose: () => void;
}

export function IPManagementFormModal({
  isOpen,
  isEdit,
  activeTab,
  listType,
  formData,
  isSubmitting,
  onFormChange,
  onSubmit,
  onClose,
}: IPManagementFormModalProps) {
  if (!isOpen) return null;

  const isBlacklist = listType === 'blacklist' || activeTab === 'blacklist';
  const title = isEdit
    ? `${listType === 'whitelist' ? '화이트리스트' : '블랙리스트'} 수정`
    : `${activeTab === 'whitelist' ? '화이트리스트' : '블랙리스트'} 추가`;

  const handleIPChange = (value: string) => {
    const formatted = value.replace(
      /(\d{1,3})\.?(\d{1,3})?\.?(\d{1,3})?\.?(\d{1,3})?/,
      (_match, p1, p2, p3, p4) => {
        const parts = [p1, p2, p3, p4].filter(Boolean);
        return parts.join('.');
      }
    );
    onFormChange({ ...formData, ip_address: formatted });
  };

  const handleDetectionDateChange = (detectionDate: string) => {
    if (detectionDate) {
      const date = new Date(detectionDate);
      date.setMonth(date.getMonth() + 3);
      const removalDate = date.toISOString().split('T')[0];
      onFormChange({ ...formData, detection_date: detectionDate, removal_date: removalDate });
    } else {
      onFormChange({ ...formData, detection_date: detectionDate });
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="form-modal-title"
      onKeyDown={(e) => e.key === 'Escape' && !isSubmitting && onClose()}
    >
      <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
        <h2 id="form-modal-title" className="text-xl font-bold mb-4">
          {title}
        </h2>

        <div className="space-y-4">
          <div>
            <label htmlFor="ip-address" className="block text-sm font-medium text-gray-700 mb-1">
              IP 주소 *
            </label>
            <input
              id="ip-address"
              type="text"
              value={formData.ip_address}
              onChange={(e) => handleIPChange(e.target.value)}
              placeholder="192.168.1.1"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              required
            />
          </div>

          <div>
            <label htmlFor="reason" className="block text-sm font-medium text-gray-700 mb-1">
              사유 <span className="text-red-500">*</span>
            </label>
            <input
              id="reason"
              type="text"
              value={formData.reason}
              onChange={(e) => onFormChange({ ...formData, reason: e.target.value })}
              placeholder={activeTab === 'whitelist' ? 'VIP 고객' : '악성 활동'}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              required
            />
          </div>

          <div>
            <label htmlFor="source" className="block text-sm font-medium text-gray-700 mb-1">
              소스
            </label>
            <select
              id="source"
              value={formData.source}
              onChange={(e) => onFormChange({ ...formData, source: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="MANUAL">수동 입력</option>
              <option value="REGTECH">REGTECH</option>
              <option value="AUTO">자동</option>
            </select>
          </div>

          {isEdit && (
            <div>
              <label htmlFor="country" className="block text-sm font-medium text-gray-700 mb-1">
                국가 코드
              </label>
              <input
                id="country"
                type="text"
                value={formData.country}
                onChange={(e) => onFormChange({ ...formData, country: e.target.value })}
                maxLength={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
          )}

          {isBlacklist && (
            <>
              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => onFormChange({ ...formData, is_active: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-sm font-medium text-gray-700">활성화</span>
                </label>
              </div>

              <div>
                <label
                  htmlFor="detection-date"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  탐지일 <span className="text-red-500">*</span>
                </label>
                <input
                  id="detection-date"
                  type="date"
                  value={formData.detection_date}
                  onChange={(e) => handleDetectionDateChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  required
                />
              </div>

              <div>
                <label
                  htmlFor="removal-date"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  해제일 (자동: 탐지일 + 3개월) <span className="text-red-500">*</span>
                </label>
                <input
                  id="removal-date"
                  type="date"
                  value={formData.removal_date}
                  onChange={(e) => onFormChange({ ...formData, removal_date: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                  placeholder="탐지일 입력 시 자동 계산됩니다"
                  required
                />
              </div>
            </>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onSubmit}
            disabled={isSubmitting}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                {isEdit ? '수정 중...' : '추가 중...'}
              </>
            ) : isEdit ? (
              '수정'
            ) : (
              '추가'
            )}
          </button>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 disabled:opacity-50"
          >
            취소
          </button>
        </div>
      </div>
    </div>
  );
}
