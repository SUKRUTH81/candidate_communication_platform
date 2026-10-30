'use client';

import React from 'react';
import {
  Alert,
  Box,
  Button,
  Divider,
  Drawer,
  IconButton,
  Paper,
  Skeleton,
  Stack,
  Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import SendIcon from '@mui/icons-material/Send';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import EmailIcon from '@mui/icons-material/Email';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { Candidate, Message } from '../types';
import { useCancelMessage, useHistory, useRetryMessages } from '../api/hooks';
import StatusChip from './StatusChip';
import { EmptyState, ErrorState } from './States';
import { formatDateTime, formatPhone, getMailtoShareUrl, getWhatsAppShareUrl } from '../utils/format';
import { useToast } from './Toast';

function timeline(m: Message): string {
  const parts: string[] = [];
  if (m.sent_at) parts.push(`Sent ${formatDateTime(m.sent_at)}`);
  if (m.delivered_at) parts.push(`Delivered ${formatDateTime(m.delivered_at)}`);
  if (m.read_at) parts.push(`Read ${formatDateTime(m.read_at)}`);
  return parts.join('  •  ');
}

function MessageCard({ m, candidate }: { m: Message; candidate?: Candidate }) {
  const retry = useRetryMessages();
  const cancel = useCancelMessage();
  const toast = useToast();
  const when = m.status === 'scheduled' ? m.scheduled_at : m.created_at;

  return (
    <Paper variant="outlined" sx={{ p: 2 }} data-testid="history-item">
      <Stack direction="row" justifyContent="space-between" alignItems="baseline" sx={{ mb: 1 }}>
        <Typography variant="subtitle2">
          {m.status === 'scheduled' ? `Scheduled for ${formatDateTime(when)}` : formatDateTime(when)}
        </Typography>
        <Stack direction="row" spacing={0.5} alignItems="center">
          <Typography variant="caption" color="text.secondary">
            {m.channel_label}
          </Typography>
          {candidate?.phone && (
            <IconButton
              size="small"
              color="success"
              title="Share on WhatsApp"
              onClick={() => window.open(getWhatsAppShareUrl(candidate.phone, m.body), '_blank', 'noopener,noreferrer')}
              sx={{ p: 0.5 }}
            >
              <WhatsAppIcon sx={{ fontSize: 16 }} />
            </IconButton>
          )}
          {candidate?.email && (
            <IconButton
              size="small"
              color="primary"
              title="Share via Email"
              onClick={() => {
                window.location.href = getMailtoShareUrl(candidate.email, 'Update regarding your application at Hunar.ai', m.body);
              }}
              sx={{ p: 0.5 }}
            >
              <EmailIcon sx={{ fontSize: 16 }} />
            </IconButton>
          )}
          <IconButton
            size="small"
            title="Copy message"
            onClick={() => {
              navigator.clipboard.writeText(m.body);
              toast('Message text copied to clipboard', 'info');
            }}
            sx={{ p: 0.5 }}
          >
            <ContentCopyIcon sx={{ fontSize: 16 }} />
          </IconButton>
        </Stack>
      </Stack>
      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', mb: 1.5 }}>
        {m.body}
      </Typography>
      <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" useFlexGap>
        <StatusChip status={m.status} />
        {m.status !== 'failed' && timeline(m) && (
          <Typography variant="caption" color="text.secondary">
            {timeline(m)}
          </Typography>
        )}
        {m.status === 'scheduled' && (
          <Button
            size="small"
            onClick={() =>
              cancel.mutate(m.id, {
                onSuccess: () => toast('Scheduled message cancelled.', 'info'),
                onError: (e: any) => toast(e.message, 'error'),
              })
            }
            disabled={cancel.isPending}
          >
            Cancel
          </Button>
        )}
      </Stack>
      {m.failure_message && (
        <Alert
          severity={m.status === 'failed' ? 'error' : 'info'}
          sx={{ mt: 1.5 }}
          action={
            m.can_retry ? (
              <Button
                color="inherit"
                size="small"
                disabled={retry.isPending}
                onClick={() =>
                  retry.mutate([m.id], {
                    onSuccess: () => toast('Retrying message…', 'info'),
                    onError: (e: any) => toast(e.message, 'error'),
                  })
                }
              >
                Retry
              </Button>
            ) : null
          }
        >
          {m.failure_message}
        </Alert>
      )}
    </Paper>
  );
}

interface HistoryDrawerProps {
  candidate: Candidate | null;
  onClose: () => void;
  onSend: (c: Candidate) => void;
}

export default function HistoryDrawer({ candidate, onClose, onSend }: HistoryDrawerProps) {
  const { data, isPending, isError, error, refetch } = useHistory(candidate?.id);
  const messages = data?.results ?? [];

  return (
    <Drawer
      anchor="right"
      open={!!candidate}
      onClose={onClose}
      slotProps={{ paper: { sx: { width: { xs: '100%', sm: 520 } } } }}
    >
      {candidate && (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ p: 3, pb: 2 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Candidate ID: {candidate.code}
              </Typography>
              <Typography variant="h6">{candidate.name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {formatPhone(candidate.phone)}
              </Typography>
              {candidate.email && (
                <Typography variant="body2" color="text.secondary">
                  {candidate.email}
                </Typography>
              )}
            </Box>
            <IconButton aria-label="Close" onClick={onClose}>
              <CloseIcon />
            </IconButton>
          </Stack>
          <Divider />
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ px: 3, py: 1.5 }}>
            <Typography variant="subtitle1" fontWeight={700}>
              Communication history
            </Typography>
            <Button
              size="small"
              variant="outlined"
              startIcon={<SendIcon />}
              onClick={() => onSend(candidate)}
            >
              New message
            </Button>
          </Stack>
          <Box sx={{ flex: 1, overflowY: 'auto', px: 3, pb: 3 }}>
            {isPending && (
              <Stack spacing={1.5}>
                {[0, 1, 2].map((i) => (
                  <Skeleton key={i} variant="rounded" height={96} />
                ))}
              </Stack>
            )}
            {isError && <ErrorState error={error} onRetry={refetch} title="Couldn't load the history" />}
            {!isPending && !isError && messages.length === 0 && (
              <EmptyState
                icon={<ChatBubbleOutlineIcon color="disabled" sx={{ fontSize: 48 }} />}
                title="No communication history"
                description="You have not communicated with this candidate yet. When you send them a message, it will appear here."
              />
            )}
            <Stack spacing={1.5}>
              {messages.map((m) => (
                <MessageCard key={m.id} m={m} candidate={candidate} />
              ))}
            </Stack>
          </Box>
        </Box>
      )}
    </Drawer>
  );
}

