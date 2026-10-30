export type MessageStatus =
  | 'scheduled'
  | 'queued'
  | 'sending'
  | 'sent'
  | 'delivered'
  | 'read'
  | 'failed'
  | 'cancelled';

export interface Candidate {
  id: string;
  name: string;
  phone: string;
  email: string;
  code: string;
  created_at: string;
  updated_at: string;
  last_message_status?: MessageStatus | null;
  last_message_at?: string | null;
  message_count?: number;
}

export interface CandidatePayload {
  name: string;
  phone: string;
  email?: string;
}

export interface Message {
  id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_phone: string;
  candidate_email: string;
  channel: string;
  channel_label: string;
  body: string;
  status: MessageStatus;
  can_retry: boolean;
  failure_code: string;
  failure_message: string;
  scheduled_at: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  read_at: string | null;
  failed_at: string | null;
  attempts: number;
  created_at: string;
  updated_at: string;
}

export interface MessageBatchResult {
  id: string;
  candidate: {
    id: string;
    name: string;
    phone: string;
    email: string;
  };
  channel: string;
  status: MessageStatus;
  can_retry: boolean;
  failure_code: string;
  failure_message: string;
  scheduled_at: string | null;
}

export interface BatchSummary {
  total: number;
  succeeded: number;
  failed: number;
  scheduled: number;
  in_progress: number;
}

export interface BatchDetail {
  id: string;
  created_at: string;
  summary: BatchSummary;
  results: MessageBatchResult[];
}

export interface MessageTemplate {
  id?: string;
  name: string;
  body: string;
  created_at?: string;
  updated_at?: string;
}

export interface ChannelMeta {
  id: string;
  label: string;
  provider: string;
  recipient: 'phone' | 'email';
}

export interface AppMeta {
  channels: ChannelMeta[];
  default_channel: string;
  max_body_length: number;
  template_variables: string[];
}

export interface ProviderStat {
  name: string;
  operational: boolean;
  channels: string[];
}

export interface ProviderHealth {
  status: 'operational' | 'degraded' | 'outage';
  worker_running: boolean;
  totals: {
    sent: number;
    delivered: number;
    read: number;
    failed: number;
    pending: number;
    scheduled: number;
  };
  providers: ProviderStat[];
}

export interface PageResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

