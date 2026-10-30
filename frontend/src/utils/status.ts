import { MessageStatus } from '../types';

export interface StatusMeta {
  label: string;
  color: 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning';
  variant: 'outlined' | 'filled';
}

export const STATUS: Record<MessageStatus, StatusMeta> = {
  scheduled: { label: 'Scheduled', color: 'secondary', variant: 'outlined' },
  queued: { label: 'Queued', color: 'default', variant: 'outlined' },
  sending: { label: 'Sending…', color: 'default', variant: 'outlined' },
  sent: { label: 'Sent', color: 'info', variant: 'filled' },
  delivered: { label: 'Delivered', color: 'success', variant: 'outlined' },
  read: { label: 'Read', color: 'success', variant: 'filled' },
  failed: { label: 'Failed', color: 'error', variant: 'filled' },
  cancelled: { label: 'Cancelled', color: 'default', variant: 'outlined' },
};

const ACTIVE = new Set<MessageStatus>(['queued', 'sending', 'sent', 'delivered']);
export const isActive = (s: MessageStatus): boolean => ACTIVE.has(s);
export const isInProgress = (s: MessageStatus): boolean => s === 'queued' || s === 'sending' || s === 'sent';

