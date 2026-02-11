'use client';

import { useState, useCallback } from 'react';

export interface IPFormData {
  ip_address: string;
  reason: string;
  source: string;
  country: string;
  is_active: boolean;
  detection_date: string;
  removal_date: string;
}

const DEFAULT_FORM_DATA: IPFormData = {
  ip_address: '',
  reason: '',
  source: 'MANUAL',
  country: '',
  is_active: true,
  detection_date: '',
  removal_date: '',
};

export function useIPForm() {
  const [formData, setFormData] = useState<IPFormData>(DEFAULT_FORM_DATA);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const resetForm = useCallback(() => {
    setFormData(DEFAULT_FORM_DATA);
    setSubmitError(null);
  }, []);

  const updateField = useCallback(<K extends keyof IPFormData>(field: K, value: IPFormData[K]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }, []);

  const formatIPAddress = useCallback((value: string): string => {
    return value.replace(
      /(\d{1,3})\.?(\d{1,3})?\.?(\d{1,3})?\.?(\d{1,3})?/,
      (_, p1, p2, p3, p4) => {
        const parts = [p1, p2, p3, p4].filter(Boolean);
        return parts.join('.');
      }
    );
  }, []);

  const handleIPChange = useCallback(
    (value: string) => {
      const formatted = formatIPAddress(value);
      setFormData((prev) => ({ ...prev, ip_address: formatted }));
    },
    [formatIPAddress]
  );

  const handleDetectionDateChange = useCallback((detectionDate: string) => {
    if (detectionDate) {
      setFormData((prev) => {
        const isRegtech = prev.source === 'REGTECH';
        // REGTECH: 수집된 해제일 유지, 그 외: 탐지일 + 3개월 자동계산
        if (isRegtech && prev.removal_date) {
          return { ...prev, detection_date: detectionDate };
        }
        const date = new Date(detectionDate);
        date.setMonth(date.getMonth() + 3);
        const removalDate = date.toISOString().split('T')[0];
        return { ...prev, detection_date: detectionDate, removal_date: removalDate };
      });
    } else {
      setFormData((prev) => ({ ...prev, detection_date: detectionDate }));
    }
  }, []);

  const populateFromRecord = useCallback(
    (record: {
      ip_address: string;
      reason: string;
      source: string;
      country?: string;
      is_active?: boolean;
      detection_date?: string;
      removal_date?: string;
    }) => {
      setFormData({
        ip_address: record.ip_address,
        reason: record.reason,
        source: record.source,
        country: record.country || '',
        is_active: record.is_active !== undefined ? record.is_active : true,
        detection_date: record.detection_date || '',
        removal_date: record.removal_date || '',
      });
      setSubmitError(null);
    },
    []
  );

  return {
    formData,
    setFormData,
    submitError,
    setSubmitError,
    resetForm,
    updateField,
    handleIPChange,
    handleDetectionDateChange,
    populateFromRecord,
  };
}
