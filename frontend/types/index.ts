export interface Statistics {
  total_ips: number;
  active_ips: number;
  recent_additions: number;
  last_update: string;
}

export interface CollectionLog {
  service_name: string;
  collection_date: string;
  items_collected: number;
  success: boolean;
  error_message?: string;
  timestamp?: string;
  source?: string;
}

export interface IPSearchResult {
  ip_address: string;
  source?: string;
  category?: string;
  country?: string;
  is_active: boolean;
  created_at: string;
  reason?: string;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  mode?: string;
}

export interface AuthStatus {
  configured: boolean;
  authenticated: boolean;
  regtech_id?: string;
}

export interface DashboardStats {
  total_ips: number;
  active_ips: number;
  whitelisted_ips: number;
  recent_additions: number;
  last_update: string | null;
  sources?: Record<string, number>;
}

export interface SystemStatus {
  service: {
    status: 'healthy' | 'unhealthy' | 'degraded';
  };
  components: {
    database: {
      status: 'healthy' | 'unhealthy' | 'degraded';
    };
  };
  collection: {
    collection_enabled: boolean;
  };
}

export interface ActivityLog {
  id?: number;
  service_name?: string;
  source: string;
  collection_date: string;
  items_collected: number;
  success: boolean;
  error_message?: string;
  timestamp?: string;
  run_count?: number;
}

export const COLLECTION_INTERVAL_OPTIONS = ['hourly', 'daily', 'weekly'] as const;

export type CollectionInterval = (typeof COLLECTION_INTERVAL_OPTIONS)[number];

export const COLLECTION_INTERVAL_SECONDS: Record<CollectionInterval, number> = {
  hourly: 3600,
  daily: 86400,
  weekly: 604800,
};

export interface CredentialPayload {
  username: string;
  password?: string;
  enabled?: boolean;
  collection_interval?: CollectionInterval;
}

export interface IPPayload {
  ip_address: string;
  reason?: string;
  source?: string;
  category?: string;
  country?: string | null;
  confidence_level?: number;
  is_active?: boolean;
}
