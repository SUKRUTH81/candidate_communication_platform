'use client';

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, qs } from './client';
import { isActive } from '../utils/status';
import {
  AppMeta,
  BatchDetail,
  Candidate,
  Message,
  MessageTemplate,
  PageResponse,
  ProviderHealth,
} from '../types';

const POLL = 3000;

export const useMeta = () =>
  useQuery<AppMeta>({
    queryKey: ['meta'],
    queryFn: () => api.get<AppMeta>('/meta/'),
    staleTime: Infinity,
  });

export const useHealth = () =>
  useQuery<ProviderHealth>({
    queryKey: ['health'],
    queryFn: () => api.get<ProviderHealth>('/provider/health/'),
    refetchInterval: 10000,
    retry: false,
  });

export function useCandidates(params: Record<string, any>) {
  return useQuery<PageResponse<Candidate>>({
    queryKey: ['candidates', params],
    queryFn: () => api.get<PageResponse<Candidate>>(`/candidates/${qs(params)}`),
    placeholderData: keepPreviousData,
    refetchInterval: (q) =>
      q.state.data?.results?.some((c) => c.last_message_status && isActive(c.last_message_status))
        ? POLL
        : false,
  });
}

export function useCreateCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; phone: string; email?: string }) =>
      api.post<Candidate>('/candidates/', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['candidates'] }),
  });
}

export function useDeleteCandidates() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) => api.post<{ deleted: number }>('/candidates/bulk-delete/', { ids }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidates'] });
      qc.invalidateQueries({ queryKey: ['messages'] });
      qc.invalidateQueries({ queryKey: ['history'] });
    },
  });
}

export function useHistory(candidateId?: string | null) {
  return useQuery<PageResponse<Message>>({
    queryKey: ['history', candidateId],
    queryFn: () => api.get<PageResponse<Message>>(`/candidates/${candidateId}/messages/?page_size=100`),
    enabled: !!candidateId,
    refetchInterval: (q) =>
      q.state.data?.results?.some((m) => isActive(m.status) || m.status === 'scheduled')
        ? POLL
        : false,
  });
}

export function useSendMessages() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      candidate_ids: string[];
      body: string;
      channel?: string;
      template_id?: string;
      scheduled_at?: string | null;
    }) => api.post<BatchDetail>('/messages/', body),
    onSuccess: () =>
      ['candidates', 'history', 'messages', 'health'].forEach((k) =>
        qc.invalidateQueries({ queryKey: [k] })
      ),
  });
}

export function useBatch(batchId?: string | null, initialData?: BatchDetail) {
  return useQuery<BatchDetail>({
    queryKey: ['batch', batchId],
    queryFn: () => api.get<BatchDetail>(`/batches/${batchId}/`),
    enabled: !!batchId,
    initialData,
    refetchInterval: (q) => (q.state.data?.summary?.in_progress ?? 0 > 0 ? 2000 : false),
  });
}

export function useMessages(params: Record<string, any>) {
  return useQuery<PageResponse<Message>>({
    queryKey: ['messages', params],
    queryFn: () => api.get<PageResponse<Message>>(`/messages/${qs(params)}`),
    placeholderData: keepPreviousData,
    refetchInterval: 5000,
  });
}

function invalidateMessaging(qc: any) {
  ['candidates', 'history', 'messages', 'batch', 'health'].forEach((k) =>
    qc.invalidateQueries({ queryKey: [k] })
  );
}

export function useRetryMessages() {
  const qc = useQueryClient();
  return useMutation<any, Error, string[]>({
    mutationFn: (ids: string[]) =>
      ids.length === 1
        ? api.post<Message>(`/messages/${ids[0]}/retry/`)
        : api.post<{ retried: number; results: any[] }>('/messages/retry/', { message_ids: ids }),
    onSuccess: () => invalidateMessaging(qc),
  });
}

export function useCancelMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post<Message>(`/messages/${id}/cancel/`),
    onSuccess: () => invalidateMessaging(qc),
  });
}

export const useTemplates = () =>
  useQuery<MessageTemplate[]>({
    queryKey: ['templates'],
    queryFn: () => api.get<MessageTemplate[]>('/templates/'),
  });

export function useSaveTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id?: string; name: string; body: string }) =>
      id ? api.patch<MessageTemplate>(`/templates/${id}/`, body) : api.post<MessageTemplate>('/templates/', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['templates'] }),
  });
}

export function useDeleteTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.del(`/templates/${id}/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['templates'] }),
  });
}
