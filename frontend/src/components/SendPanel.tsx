'use client';

import React, { useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Drawer,
  FormControlLabel,
  IconButton,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import EmailIcon from '@mui/icons-material/Email';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { Candidate, BatchDetail } from '../types';
import { useMeta, useSendMessages, useTemplates } from '../api/hooks';
import RecipientChips from './RecipientChips';
import { formatDateTime, getMailtoShareUrl, getWhatsAppShareUrl, plural, renderPreview, toLocalInputValue } from '../utils/format';

interface SendPanelProps {
  recipients: Candidate[];
  open: boolean;
  onClose: () => void;
  onSent: (result: BatchDetail, metaInfo: { scheduled: boolean; when?: string; recipients: Candidate[] }) => void;
}

export default function SendPanel({ recipients: initial, open, onClose, onSent }: SendPanelProps) {
  const { data: meta } = useMeta();
  const { data: templates = [] } = useTemplates();
  const send = useSendMessages();
  const [recipients, setRecipients] = useState<Candidate[]>(initial);
  const [body, setBody] = useState('');
  const [channel, setChannel] = useState('');
  const [templateId, setTemplateId] = useState('');
  const [schedule, setSchedule] = useState(false);
  const [when, setWhen] = useState(() => toLocalInputValue(new Date(Date.now() + 3600 * 1000)));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState('');
  const [shareCopied, setShareCopied] = useState(false);
  const textRef = useRef<HTMLTextAreaElement>(null);

  const maxLen = meta?.max_body_length ?? 1600;
  const activeChannel = channel || meta?.default_channel || 'whatsapp';
  const channelMeta = meta?.channels?.find((c) => c.id === activeChannel);
  const lacking = useMemo(
    () => (channelMeta?.recipient === 'email' ? recipients.filter((r) => !r.email) : []),
    [channelMeta, recipients]
  );
  const hasPlaceholders = /\{\{\s*[A-Za-z_]+\s*\}\}/.test(body);

  const insert = (token: string) => {
    const el = textRef.current;
    const start = el?.selectionStart ?? body.length;
    const end = el?.selectionEnd ?? body.length;
    const next = body.slice(0, start) + token + body.slice(end);
    setBody(next);
    setErrors((e) => ({ ...e, body: undefined as any }));
    requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(start + token.length, start + token.length);
    });
  };

  const pickTemplate = (id: string) => {
    setTemplateId(id);
    const t = templates.find((x) => x.id === id);
    if (t) {
      setBody(t.body);
      setErrors((e) => ({ ...e, body: undefined as any }));
    }
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!body.trim()) errs.body = 'Write a message before sending.';
    else if (body.length > maxLen) errs.body = `Messages can be at most ${maxLen} characters.`;
    let scheduledAt: string | undefined;
    if (schedule) {
      const d = new Date(when);
      if (!when || Number.isNaN(d.getTime())) errs.scheduled_at = 'Pick a date and time.';
      else if (d.getTime() < Date.now() + 60_000) errs.scheduled_at = 'Pick a time at least a minute from now.';
      else scheduledAt = d.toISOString();
    }
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setFormError('');
    send.mutate(
      {
        candidate_ids: recipients.map((r) => r.id),
        body: body.trim(),
        channel: activeChannel,
        template_id: templateId || undefined,
        scheduled_at: scheduledAt,
      },
      {
        onSuccess: (result) => onSent(result, { scheduled: !!scheduledAt, when: scheduledAt, recipients }),
        onError: (err: any) => {
          if (err.fields && Object.keys(err.fields).length) setErrors(err.fields);
          if (!err.fields?.body && !err.fields?.scheduled_at)
            setFormError(err.fields?.candidate_ids || err.message || 'Failed to send message.');
        },
      }
    );
  };

  const tooMany = (meta as any)?.max_bulk_recipients && recipients.length > (meta as any).max_bulk_recipients;

  const placeholders = (meta as any)?.placeholders || [
    { key: 'first_name', label: 'First Name' },
    { key: 'name', label: 'Full Name' },
    { key: 'phone', label: 'Phone' },
  ];

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={() => !send.isPending && onClose()}
      slotProps={{ paper: { sx: { width: { xs: '100%', sm: 460 } } } }}
    >
      <Box
        component="form"
        onSubmit={submit}
        noValidate
        sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}
      >
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ px: 3, py: 2 }}>
          <Typography variant="h6">Send message</Typography>
          <IconButton aria-label="Close" onClick={onClose} disabled={send.isPending}>
            <CloseIcon />
          </IconButton>
        </Stack>
        <Divider />

        <Stack spacing={2.5} sx={{ p: 3, flex: 1, overflowY: 'auto' }}>
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {plural(recipients.length, 'Recipient')}
            </Typography>
            <RecipientChips
              recipients={recipients}
              onRemove={(r) => setRecipients((rs) => rs.filter((x) => x.id !== r.id))}
            />
          </Box>

          {tooMany && (
            <Alert severity="warning">
              You can message up to {(meta as any).max_bulk_recipients} candidates at once. Remove a few recipients to continue.
            </Alert>
          )}
          {lacking.length > 0 && (
            <Alert severity="warning">
              {plural(lacking.length, 'recipient')} {lacking.length === 1 ? 'has' : 'have'} no email address, so{' '}
              {lacking.length === 1 ? 'that message' : 'those messages'} will fail. Switch channel or remove them.
            </Alert>
          )}

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField
              select
              size="small"
              fullWidth
              label="Send via"
              value={activeChannel}
              onChange={(e) => setChannel(e.target.value)}
            >
              {(meta?.channels || [{ id: 'whatsapp', label: 'WhatsApp' }]).map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              size="small"
              fullWidth
              label="Use a template"
              value={templateId}
              onChange={(e) => pickTemplate(e.target.value)}
              disabled={!templates.length}
            >
              <MenuItem value="">
                <em>{templates.length ? 'None' : 'No templates yet'}</em>
              </MenuItem>
              {templates.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name}
                </MenuItem>
              ))}
            </TextField>
          </Stack>

          <TextField
            label="Message"
            required
            multiline
            rows={8}
            fullWidth
            value={body}
            onChange={(e) => {
              setBody(e.target.value);
              setErrors((er) => ({ ...er, body: undefined as any }));
            }}
            placeholder="Type or paste here..."
            error={!!errors.body}
            helperText={errors.body || 'Type, or paste the message you want to send.'}
            inputRef={textRef}
            disabled={send.isPending}
            sx={{ '& textarea': { resize: 'vertical' } }}
          />
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap alignItems="center">
              <Typography variant="caption" color="text.secondary">
                Insert:
              </Typography>
              {placeholders.slice(0, 3).map((p: any) => (
                <Chip
                  key={p.key}
                  size="small"
                  variant="outlined"
                  label={p.label}
                  onClick={() => insert(`{{${p.key}}}`)}
                />
              ))}
            </Stack>
            <Typography variant="caption" color={body.length > maxLen ? 'error' : 'text.secondary'}>
              {body.length}/{maxLen}
            </Typography>
          </Stack>

          {hasPlaceholders && recipients[0] && (
            <Box sx={{ p: 1.5, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Preview for {recipients[0].name}
              </Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {renderPreview(body, recipients[0])}
              </Typography>
            </Box>
          )}

          <Box>
            <FormControlLabel
              control={<Switch checked={schedule} onChange={(e) => setSchedule(e.target.checked)} />}
              label="Schedule for later"
            />
            {schedule && (
              <TextField
                type="datetime-local"
                size="small"
                fullWidth
                label="Send at"
                value={when}
                onChange={(e) => {
                  setWhen(e.target.value);
                  setErrors((er) => ({ ...er, scheduled_at: undefined as any }));
                }}
                error={!!errors.scheduled_at}
                helperText={
                  errors.scheduled_at ||
                  `Your local time${when ? ` • ${formatDateTime(new Date(when).toISOString())}` : ''}`
                }
                slotProps={{
                  inputLabel: { shrink: true },
                  htmlInput: { min: toLocalInputValue(new Date(Date.now() + 60_000)) },
                }}
                sx={{ mt: 1 }}
              />
            )}
          </Box>
          {formError && <Alert severity="error">{formError}</Alert>}
        </Stack>

        <Divider />
        {recipients.length > 0 && (
          <Box sx={{ px: 2.5, py: 1.5, bgcolor: '#f8fafc', borderTop: '1px solid #e2e8f0' }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, fontWeight: 600 }}>
              ⚡ Real Message Sharing
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {recipients[0]?.phone && (
                <Button
                  variant="outlined"
                  color="success"
                  size="small"
                  startIcon={<WhatsAppIcon />}
                  onClick={() => {
                    const rendered = renderPreview(body, recipients[0]);
                    window.open(getWhatsAppShareUrl(recipients[0].phone, rendered), '_blank', 'noopener,noreferrer');
                  }}
                  disabled={!body.trim()}
                >
                  WhatsApp
                </Button>
              )}
              {recipients[0]?.email && (
                <Button
                  variant="outlined"
                  color="primary"
                  size="small"
                  startIcon={<EmailIcon />}
                  onClick={() => {
                    const rendered = renderPreview(body, recipients[0]);
                    window.location.href = getMailtoShareUrl(recipients[0].email, 'Update regarding your application at Hunar.ai', rendered);
                  }}
                  disabled={!body.trim()}
                >
                  Email
                </Button>
              )}
              <Button
                variant="outlined"
                color="inherit"
                size="small"
                startIcon={<ContentCopyIcon />}
                onClick={() => {
                  const rendered = renderPreview(body, recipients[0]);
                  navigator.clipboard.writeText(rendered);
                  setShareCopied(true);
                  setTimeout(() => setShareCopied(false), 2000);
                }}
                disabled={!body.trim()}
              >
                {shareCopied ? 'Copied!' : 'Copy Text'}
              </Button>
            </Stack>
          </Box>
        )}
        <Box sx={{ p: 2.5 }}>
          <Button
            type="submit"
            variant="contained"
            size="large"
            fullWidth
            disabled={send.isPending || recipients.length === 0 || !!tooMany}
            startIcon={send.isPending ? <CircularProgress size={18} color="inherit" /> : null}
          >
            {send.isPending ? 'Sending…' : schedule ? 'Schedule Message' : 'Send Message'}
          </Button>
        </Box>
      </Box>
    </Drawer>
  );
}

