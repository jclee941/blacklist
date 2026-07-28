'use client';

import {
  useIPManagement,
  IPManagementTabs,
  IPManagementFilters,
  IPManagementTable,
  IPManagementFormModal,
  DeleteConfirmModal,
} from './components';

export default function IPManagementClient() {
  const {
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
  } = useIPManagement();

  const handleSearchReset = () => {
    setSearchIP('');
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {submitSuccess && (
        <div className="rounded-md bg-green-50 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-green-800">
                {activeTab === 'whitelist' ? '화이트리스트' : '블랙리스트'} 항목이 성공적으로
                추가/수정되었습니다.
              </p>
            </div>
          </div>
        </div>
      )}

      {submitError && (
        <div className="rounded-md bg-red-50 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-red-800">오류: {submitError}</p>
            </div>
          </div>
        </div>
      )}

      <IPManagementTabs activeTab={activeTab} onTabChange={changeTab} />

      <IPManagementFilters
        activeTab={activeTab}
        filterType={filterType}
        filterSource={filterSource}
        searchIP={searchIP}
        isDownloading={isDownloading}
        onFilterTypeChange={setFilterType}
        onFilterSourceChange={setFilterSource}
        onSearchIPChange={setSearchIP}
        onSearch={fetchData}
        onReset={handleSearchReset}
        onDownload={downloadRawData}
        onAdd={openAddModal}
      />

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <IPManagementTable
          activeTab={activeTab}
          data={data}
          loading={loading}
          page={page}
          total={total}
          totalPages={totalPages}
          onPageChange={setPage}
          onEdit={openEditModal}
          onDelete={confirmDelete}
        />
      </div>

      <IPManagementFormModal
        isOpen={showAddModal}
        isEdit={false}
        activeTab={activeTab}
        listType={activeTab === 'whitelist' ? 'whitelist' : 'blacklist'}
        formData={formData}
        isSubmitting={isSubmitting}
        onFormChange={setFormData}
        onSubmit={handleAdd}
        onClose={closeAddModal}
      />

      <IPManagementFormModal
        isOpen={showEditModal}
        isEdit={true}
        activeTab={activeTab}
        listType={editingRecord?.list_type === 'whitelist' ? 'whitelist' : 'blacklist'}
        formData={formData}
        isSubmitting={isSubmitting}
        onFormChange={setFormData}
        onSubmit={handleEdit}
        onClose={closeEditModal}
      />

      <DeleteConfirmModal
        isOpen={showDeleteModal}
        record={deletingRecord}
        onConfirm={handleDelete}
        onClose={closeDeleteModal}
      />
    </div>
  );
}
