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

export interface BlacklistStats {
  total_ips: number;
  sources: Array<{ source: string; count: number }>;
  last_update: string;
}

export interface CredentialFormData {
  username: string;
  password: string;
  enabled: boolean;
  collection_interval: string;
}

export const COLLECTORS = ['REGTECH', 'SECUDIUM'] as const;
export type CollectorType = (typeof COLLECTORS)[number];
