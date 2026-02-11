'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  getUnifiedIPs,
  getWhitelist,
  getBlacklist,
  addIP,
  updateIP,
  deleteIP,
  exportBlacklistRaw,
} from '@/lib/api';
import { IPRecord, IPFormData, TabType, ListType, INITIAL_FORM_DATA, IPRequestBody } from './types';

interface ApiPagination {
  total?: number;
  total_pages?: number;
  pages?: number;
}

interface ApiResponse {
  success?: boolean;
  error?: string;
  data?:
    | {
        items?: IPRecord[];
        pagination?: ApiPagination;
      }
    | IPRecord[];
  pagination?: ApiPagination;
}

export function useIPManagement() {
  const [activeTab, setActiveTab] = useState<TabType>('unified');
  const [data, setData] = useState<IPRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [editingRecord, setEditingRecord] = useState<IPRecord | null>(null);
  const [deletingRecord, setDeletingRecord] = useState<IPRecord | null>(null);

  const [formData, setFormData] = useState<IPFormData>(INITIAL_FORM_DATA);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [filterType, setFilterType] = useState<string>('');
  const [filterSource, setFilterSource] = useState<string>('');
  const [searchIP, setSearchIP] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: page.toString(), limit: '20' });
      let json: ApiResponse | undefined;

      if (activeTab === 'unified') {
        if (filterType) params.append('type', filterType);
        if (filterSource) params.append('source', filterSource);
        if (searchIP) params.append('ip', searchIP);
        json = await getUnifiedIPs(params.toString());
      } else if (activeTab === 'whitelist') {
        json = await getWhitelist(params.toString());
      } else {
        json = await getBlacklist(params.toString());
      }

      if (json && json.success !== false) {
        const responseData = json.data;
        let items: IPRecord[] = [];
        let pagination: ApiPagination = {};

        if (Array.isArray(responseData)) {
          items = responseData;
          pagination = json.pagination || {};
        } else if (responseData) {
          items = responseData.items || [];
          pagination = responseData.pagination || json.pagination || {};
        }

        setData(items);
        setTotal(pagination.total || 0);
        setTotalPages(pagination.total_pages || pagination.pages || 0);
      }
    } catch (error) {
      console.error('Fetch error:', error);
    } finally {
      setLoading(false);
    }
  }, [activeTab, page, filterType, filterSource, searchIP]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const resetForm = useCallback(() => {
    setFormData(INITIAL_FORM_DATA);
    setSubmitError(null);
  }, []);

  const handleAdd = async () => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const listType: ListType =
        activeTab === 'whitelist' || activeTab === 'unified' ? 'whitelist' : 'blacklist';
      const body: IPRequestBody = {
        ip_address: formData.ip_address,
        reason: formData.reason,
        source: formData.source,
        country: formData.country || null,
      };

      if (listType === 'blacklist') {
        body.is_active = formData.is_active;
        if (formData.detection_date) body.detection_date = formData.detection_date;
        if (formData.removal_date) body.removal_date = formData.removal_date;
      }

      const json = await addIP(listType, body);

      if (json.success) {
        setSubmitSuccess(true);
        setShowAddModal(false);
        resetForm();
        fetchData();
        setTimeout(() => setSubmitSuccess(false), 3000);
      } else {
        setSubmitError(json.error || '알 수 없는 오류가 발생했습니다.');
      }
    } catch (error) {
      setSubmitError(`추가 실패: ${error}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEdit = async () => {
    if (!editingRecord) return;
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const listType: ListType =
        editingRecord.list_type === 'whitelist' ? 'whitelist' : 'blacklist';
      const body: IPRequestBody = {
        ip_address: formData.ip_address,
        reason: formData.reason,
        source: formData.source,
        country: formData.country || null,
      };

      if (listType === 'blacklist') {
        body.is_active = formData.is_active;
        if (formData.detection_date) body.detection_date = formData.detection_date;
        if (formData.removal_date) body.removal_date = formData.removal_date;
      }

      const json = await updateIP(listType, editingRecord.id, body);

      if (json.success) {
        setSubmitSuccess(true);
        setShowEditModal(false);
        setEditingRecord(null);
        resetForm();
        fetchData();
        setTimeout(() => setSubmitSuccess(false), 3000);
      } else {
        setSubmitError(json.error || '알 수 없는 오류가 발생했습니다.');
      }
    } catch (error) {
      setSubmitError(`수정 실패: ${error}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!deletingRecord) return;

    try {
      const listType: ListType =
        deletingRecord.list_type === 'whitelist' || activeTab === 'whitelist'
          ? 'whitelist'
          : 'blacklist';
      const json = await deleteIP(listType, deletingRecord.id);

      if (json.success) {
        setSubmitSuccess(true);
        setShowDeleteModal(false);
        setDeletingRecord(null);
        fetchData();
        setTimeout(() => setSubmitSuccess(false), 3000);
      } else {
        setSubmitError(json.error || '삭제에 실패했습니다.');
        setTimeout(() => setSubmitError(null), 5000);
      }
    } catch (error) {
      setSubmitError(`삭제 실패: ${error}`);
      setTimeout(() => setSubmitError(null), 5000);
    } finally {
      setShowDeleteModal(false);
      setDeletingRecord(null);
    }
  };

  const openEditModal = (record: IPRecord) => {
    setEditingRecord(record);
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
    setShowEditModal(true);
  };

  const confirmDelete = (record: IPRecord) => {
    setDeletingRecord(record);
    setShowDeleteModal(true);
  };

  const downloadRawData = async () => {
    setIsDownloading(true);
    try {
      const params = new URLSearchParams();
      if (activeTab === 'blacklist') {
        params.append('active_only', 'false');
      }

      const blob = await exportBlacklistRaw(params.toString());
      if (!blob) throw new Error('Download failed');

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `blacklist_raw_data_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      setSubmitError(`다운로드 실패: ${error}`);
      setTimeout(() => setSubmitError(null), 5000);
    } finally {
      setIsDownloading(false);
    }
  };

  const changeTab = (tab: TabType) => {
    setActiveTab(tab);
    setPage(1);
  };

  const openAddModal = () => {
    setShowAddModal(true);
    resetForm();
  };

  const closeAddModal = () => {
    setShowAddModal(false);
    resetForm();
  };

  const closeEditModal = () => {
    setShowEditModal(false);
    setEditingRecord(null);
    resetForm();
  };

  const closeDeleteModal = () => {
    setShowDeleteModal(false);
    setDeletingRecord(null);
  };

  return {
    activeTab,
    data,
    loading,
    page,
    total,
    totalPages,
    showAddModal,
    showEditModal,
    showDeleteModal,
    editingRecord,
    deletingRecord,
    formData,
    isSubmitting,
    submitSuccess,
    submitError,
    filterType,
    filterSource,
    searchIP,
    isDownloading,
    setPage,
    setFormData,
    setFilterType,
    setFilterSource,
    setSearchIP,
    changeTab,
    fetchData,
    handleAdd,
    handleEdit,
    handleDelete,
    openEditModal,
    confirmDelete,
    downloadRawData,
    openAddModal,
    closeAddModal,
    closeEditModal,
    closeDeleteModal,
  };
}
