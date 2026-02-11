'use client';

import { IPFormData } from '../hooks/use-ip-form';

interface IPFormFieldsProps {
  formData: IPFormData;
  onIPChange: (value: string) => void;
  onReasonChange: (value: string) => void;
  onSourceChange: (value: string) => void;
  onCountryChange?: (value: string) => void;
  onActiveChange?: (value: boolean) => void;
  onDetectionDateChange?: (value: string) => void;
  onRemovalDateChange?: (value: string) => void;
  showBlacklistFields: boolean;
  placeholderReason?: string;
  idPrefix?: string;
}

export function IPFormFields({
  formData,
  onIPChange,
  onReasonChange,
  onSourceChange,
  onCountryChange,
  onActiveChange,
  onDetectionDateChange,
  onRemovalDateChange,
  showBlacklistFields,
  placeholderReason = '악성 활동',
  idPrefix = 'ip-form',
}: IPFormFieldsProps) {
  return (
    <div className="space-y-4">
      <div>
        <label htmlFor={`${idPrefix}-ip`} className="block text-sm font-medium text-gray-700 mb-1">
          IP 주소 *
        </label>
        <input
          id={`${idPrefix}-ip`}
          type="text"
          value={formData.ip_address}
          onChange={(e) => onIPChange(e.target.value)}
          placeholder="192.168.1.1"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          required
        />
      </div>

      <div>
        <label
          htmlFor={`${idPrefix}-reason`}
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          사유 <span className="text-red-500">*</span>
        </label>
        <input
          id={`${idPrefix}-reason`}
          type="text"
          value={formData.reason}
          onChange={(e) => onReasonChange(e.target.value)}
          placeholder={placeholderReason}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          required
        />
      </div>

      <div>
        <label
          htmlFor={`${idPrefix}-source`}
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          소스
        </label>
        <select
          id={`${idPrefix}-source`}
          value={formData.source}
          onChange={(e) => onSourceChange(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg"
        >
          <option value="MANUAL">수동 입력</option>
          <option value="REGTECH">REGTECH</option>
          <option value="SECUDIUM">SECUDIUM</option>
          <option value="AUTO">자동</option>
        </select>
      </div>

      {onCountryChange && (
        <div>
          <label
            htmlFor={`${idPrefix}-country`}
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            국가 코드
          </label>
          <input
            id={`${idPrefix}-country`}
            type="text"
            value={formData.country}
            onChange={(e) => onCountryChange(e.target.value.toUpperCase())}
            placeholder="KR"
            maxLength={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
      )}

      {showBlacklistFields && (
        <>
          {onActiveChange && (
            <div>
              <label htmlFor={`${idPrefix}-active`} className="flex items-center gap-2">
                <input
                  id={`${idPrefix}-active`}
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => onActiveChange(e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm font-medium text-gray-700">활성화</span>
              </label>
            </div>
          )}

          {onDetectionDateChange && (
            <div>
              <label
                htmlFor={`${idPrefix}-detection`}
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                탐지일 <span className="text-red-500">*</span>
              </label>
              <input
                id={`${idPrefix}-detection`}
                type="date"
                value={formData.detection_date}
                onChange={(e) => onDetectionDateChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                required
              />
            </div>
          )}

          {onRemovalDateChange && (
            <div>
              <label
                htmlFor={`${idPrefix}-removal`}
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                해제일{formData.source !== 'REGTECH' ? ' (자동: 탐지일 + 3개월)' : ''}{' '}
                <span className="text-red-500">*</span>
              </label>
              <input
                id={`${idPrefix}-removal`}
                type="date"
                value={formData.removal_date}
                onChange={(e) => onRemovalDateChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                required
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}
