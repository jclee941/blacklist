export interface IPRecord {
  id: number;
  ip_address: string;
  reason: string;
  source: string;
  data_source?: string;
  confidence_level?: number;
  detection_count?: number;
  last_seen?: string;
  country?: string;
  is_active?: boolean;
  detection_date?: string;
  removal_date?: string;
  created_at: string;
  updated_at: string;
  list_type?: string;
}

export interface IPRequestBody {
  ip_address: string;
  reason: string;
  source: string;
  country: string | null;
  is_active?: boolean;
  detection_date?: string;
  removal_date?: string;
  [key: string]: unknown;
}

export interface IPFormData {
  ip_address: string;
  reason: string;
  source: string;
  country: string;
  is_active: boolean;
  detection_date: string;
  removal_date: string;
}

export type TabType = 'unified' | 'whitelist' | 'blacklist';
export type ListType = 'whitelist' | 'blacklist';

export const INITIAL_FORM_DATA: IPFormData = {
  ip_address: '',
  reason: '',
  source: 'MANUAL',
  country: '',
  is_active: true,
  detection_date: '',
  removal_date: '',
};
