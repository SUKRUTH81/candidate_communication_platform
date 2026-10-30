'use client';

import React from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
} from '@mui/material';
import { BatchDetail } from '../types';
import { useBatch, useRetryMessages } from '../api/hooks';
import StatusChip from './StatusChip';
import { formatPhone, formatDateTime } from '../utils/format';
import { useToast } from './Toast';

interface BulkResultDialogProps {
  batchId?: string | null;
  initial?: BatchDetail;
  onClose: () => void;
}

export default function BulkResultDialog({ batchId, initial, onClose }: BulkResultDialogProps) {
  const { data, isError, error, refetch } = useBatch(batchId, initial);
  const retry = useRetryMessages();
  const toast = useToast();
  if (!data) return null;

  const { summary, results } = data;
  const scheduled = summary.scheduled === summary.total;
  const retryable = results.filter((r) => r.can_retry);
  const finished = summary.total - summary.in_progress;

  const doRetry = (ids: string[]) =>
    retry.mutate(ids, {
      onSuccess: (r: any) => {
        if (r.results && r.retried < ids.length)
          toast(`${r.retried} of ${ids.length} queued again. The rest can't be retried.`, 'warning');
        else toast(ids.length === 1 ? 'Retrying message…' : `Retrying ${ids.length} messages…`, 'info');
      },
      onError: (e: any) => toast(e.message, 'error'),
    });

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm" aria-labelledby="result-title">
      <DialogTitle id="result-title" sx={{ fontWeight: 700 }}>
        {scheduled ? 'Messages scheduled' : 'Message results'}
      </DialogTitle>
      <DialogContent dividers>
        <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
          <Chip label={`${summary.total} total`} variant="outlined" />
          {summary.scheduled > 0 && (
            <Chip label={`${summary.scheduled} scheduled`} color="secondary" variant="outlined" />
          )}
          <Chip label={`${summary.succeeded} delivered`} color="success" variant="outlined" />
          {summary.in_progress > 0 && (
            <Chip label={`${summary.in_progress} in progress`} variant="outlined" />
          )}
          {summary.failed > 0 && <Chip label={`${summary.failed} failed`} color="error" />}
        </Stack>

        {summary.in_progress > 0 && (
          <Box sx={{ mb: 2 }}>
            <LinearProgress variant="determinate" value={(finished / summary.total) * 100} />
            <Typography variant="caption" color="text.secondary">
              {finished} of {summary.total} finished — statuses update automatically.
            </Typography>
          </Box>
        )}
        {isError && (
          <Alert
            severity="warning"
            sx={{ mb: 2 }}
            action={
              <Button size="small" onClick={() => refetch()}>
                Retry
              </Button>
            }
          >
            {(error as any)?.message || 'Failed to update.'}
          </Alert>
        )}
        {summary.failed > 0 && summary.failed < summary.total && (
          <Alert severity="info" sx={{ mb: 2 }}>
            The other messages were not affected — each candidate is sent independently.
          </Alert>
        )}

        <List disablePadding sx={{ maxHeight: 360, overflowY: 'auto' }}>
          {results.map((r) => (
            <ListItem
              key={r.id}
              divider
              disableGutters
              secondaryAction={
                r.can_retry ? (
                  <Button size="small" onClick={() => doRetry([r.id])} disabled={retry.isPending}>
                    Retry
                  </Button>
                ) : null
              }
              sx={{ pr: r.can_retry ? 9 : 0, alignItems: 'flex-start' }}
            >
              <ListItemText
                primary={
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                    <strong>{r.candidate.name}</strong>
                    <StatusChip status={r.status} />
                  </Stack>
                }
                secondary={
                  <div>
                    <Typography variant="caption" component="span" color="text.secondary">
                      {formatPhone(r.candidate.phone)}
                      {r.status === 'scheduled' && ` • sends ${formatDateTime(r.scheduled_at)}`}
                    </Typography>
                    {r.failure_message && (
                      <Typography
                        variant="body2"
                        component="span"
                        display="block"
                        color={r.status === 'failed' ? 'error' : 'text.secondary'}
                      >
                        {r.failure_message}
                      </Typography>
                    )}
                  </div>
                }
              />
            </ListItem>
          ))}
        </List>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2 }}>
        {retryable.length > 1 && (
          <Button onClick={() => doRetry(retryable.map((r) => r.id))} disabled={retry.isPending}>
            Retry {retryable.length} failed
          </Button>
        )}
        <Button variant="contained" onClick={onClose}>
          Done
        </Button>
      </DialogActions>
    </Dialog>
  );
}

