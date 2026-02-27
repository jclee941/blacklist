export interface CollectorStatus {
  enabled: boolean;
  error_count: number;
  interval_seconds: number;
  last_run: string | null;
  next_run: string | null;
  run_count: number;
}

export interface Credential {
  service_name: string;
  username: string;
  enabled: boolean;
  collection_interval?: string;
  last_collection?: string;
  connection_status?: 'connected' | 'locked' | 'failed' | 'unknown';
  status_message?: string;
}

export interface CollectionStatus {
  is_running: boolean;
  collectors: Record<string, CollectorStatus>;
}

export interface SourceStats {
  count?: number;
  total_items?: number;
  total_collections?: number;
  cumulative_collected?: number;
  success_rate?: number;
  last_collection?: string;
  avg_duration?: number;
}

export interface BlacklistStats {
  current_total_ips: number;
  current_active_ips: number;
  today_collected: number;
  week_collected: number;
  month_collected: number;
  sources: Record<string, SourceStats>;
}

export interface CredentialFormState {
  username: string;
  password: string;
  enabled: boolean;
  collection_interval: string;
}

export interface NotificationState {
  type: 'success' | 'error';
  message: string;
}
