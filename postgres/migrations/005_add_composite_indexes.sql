CREATE INDEX IF NOT EXISTS idx_blacklist_ips_ip_active ON blacklist_ips(ip_address, is_active);
CREATE INDEX IF NOT EXISTS idx_blacklist_ips_active_created ON blacklist_ips(is_active, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_blacklist_ips_active_data_source ON blacklist_ips(is_active, data_source);
CREATE INDEX IF NOT EXISTS idx_blacklist_ips_confidence_detection ON blacklist_ips(confidence_level DESC, detection_date DESC);
CREATE INDEX IF NOT EXISTS idx_collection_history_service_date ON collection_history(service_name, collection_date DESC);
CREATE INDEX IF NOT EXISTS idx_collection_history_success_date ON collection_history(success, collection_date DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_level_timestamp ON system_logs(level, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_fortigate_pull_logs_device_request ON fortigate_pull_logs(device_ip, last_request_at DESC);
CREATE INDEX IF NOT EXISTS idx_unified_ip_list_type_active ON unified_ip_list(list_type, is_active);
