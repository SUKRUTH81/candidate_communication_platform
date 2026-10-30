'use client';

import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Skeleton,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import { MessageTemplate } from '../types';
import { useDeleteTemplate, useMeta, useSaveTemplate, useTemplates } from '../api/hooks';
import { EmptyState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { renderPreview } from '../utils/format';

const SAMPLE = { name: 'Rahul Sharma', phone: '+919876543210', email: 'rahul@example.com', code: 'A1B2C3' };

interface TemplateDialogProps {
  template: Partial<MessageTemplate>;
  onClose: () => void;
}

function TemplateDialog({ template, onClose }: TemplateDialogProps) {
  const { data: meta } = useMeta();
  const save = useSaveTemplate();
  const toast = useToast();
  const [name, setName] = useState(template?.name ?? '');
  const [body, setBody] = useState(template?.body ?? '');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!name.trim()) errs.name = 'Give the template a name.';
    if (!body.trim()) errs.body = 'Write the template text.';
    setErrors(errs);
    if (Object.keys(errs).length) return;
    save.mutate(
      { id: template?.id, name: name.trim(), body },
      {
        onSuccess: () => {
          toast(template?.id ? 'Template updated.' : 'Template created.');
          onClose();
        },
        onError: (err: any) =>
          setErrors(Object.keys(err.fields || {}).length ? err.fields : { form: err.message }),
      }
    );
  };

  const placeholders = (meta as any)?.placeholders || [
    { key: 'first_name', label: 'First Name' },
    { key: 'name', label: 'Full Name' },
    { key: 'phone', label: 'Phone' },
  ];

  return (
    <Dialog
      open
      onClose={() => !save.isPending && onClose()}
      fullWidth
      maxWidth="sm"
      PaperProps={{ component: 'form', onSubmit: submit } as any}
    >
      <DialogTitle sx={{ fontWeight: 700 }}>
        {template?.id ? 'Edit template' : 'New template'}
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          {errors.form && <Alert severity="error">{errors.form}</Alert>}
          <TextField
            label="Template name"
            required
            autoFocus
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setErrors((x) => ({ ...x, name: undefined as any }));
            }}
            error={!!errors.name}
            helperText={errors.name}
            inputProps={{ maxLength: 80 }}
          />
          <TextField
            label="Message"
            required
            multiline
            rows={6}
            value={body}
            onChange={(e) => {
              setBody(e.target.value);
              setErrors((x) => ({ ...x, body: undefined as any }));
            }}
            error={!!errors.body}
            helperText={errors.body || 'Use placeholders to personalise each message.'}
            sx={{ '& textarea': { resize: 'vertical' } }}
          />
          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap alignItems="center">
            <Typography variant="caption" color="text.secondary">
              Insert:
            </Typography>
            {placeholders.map((p: any) => (
              <Chip
                key={p.key}
                size="small"
                variant="outlined"
                label={p.label}
                onClick={() => setBody((b) => `${b}{{${p.key}}}`)}
              />
            ))}
          </Stack>
          {body && (
            <Box sx={{ p: 1.5, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Preview for {SAMPLE.name}
              </Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {renderPreview(body, SAMPLE)}
              </Typography>
            </Box>
          )}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={save.isPending}>
          Cancel
        </Button>
        <Button
          type="submit"
          variant="contained"
          disabled={save.isPending}
          startIcon={save.isPending ? <CircularProgress size={16} color="inherit" /> : null}
        >
          Save template
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default function TemplatesPage() {
  const { data, isPending, isError, error, refetch } = useTemplates();
  const del = useDeleteTemplate();
  const toast = useToast();
  const [editing, setEditing] = useState<Partial<MessageTemplate> | null>(null);
  const [confirm, setConfirm] = useState<MessageTemplate | null>(null);

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">Message templates</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setEditing({})}>
          New template
        </Button>
      </Stack>
      {isPending && (
        <Stack spacing={2}>
          {[0, 1].map((i) => (
            <Skeleton key={i} variant="rounded" height={120} />
          ))}
        </Stack>
      )}
      {isError && <ErrorState error={error} onRetry={refetch} title="Couldn't load templates" />}
      {data?.length === 0 && (
        <EmptyState
          icon={<DescriptionOutlinedIcon color="disabled" sx={{ fontSize: 56 }} />}
          title="No templates yet"
          description="Save the messages you send often, with placeholders like {{first_name}}, and reuse them in one click."
        />
      )}
      <Box
        sx={{
          display: 'grid',
          gap: 2,
          gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' },
        }}
      >
        {data?.map((t) => (
          <Card key={t.id} variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700}>
                {t.name}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  whiteSpace: 'pre-wrap',
                  display: '-webkit-box',
                  WebkitLineClamp: 5,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                }}
              >
                {t.body}
              </Typography>
            </CardContent>
            <CardActions sx={{ justifyContent: 'flex-end' }}>
              <Tooltip title="Edit">
                <IconButton aria-label={`Edit ${t.name}`} onClick={() => setEditing(t)}>
                  <EditIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Delete">
                <IconButton aria-label={`Delete ${t.name}`} onClick={() => setConfirm(t)}>
                  <DeleteIcon />
                </IconButton>
              </Tooltip>
            </CardActions>
          </Card>
        ))}
      </Box>
      {editing && <TemplateDialog template={editing} onClose={() => setEditing(null)} />}
      <Dialog open={!!confirm} onClose={() => setConfirm(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Delete “{confirm?.name}”?</DialogTitle>
        <DialogContent>
          <Typography>Messages already sent from this template aren't affected.</Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setConfirm(null)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            disabled={del.isPending}
            onClick={() =>
              confirm?.id &&
              del.mutate(confirm.id, {
                onSuccess: () => {
                  toast('Template deleted.');
                  setConfirm(null);
                },
                onError: (e: any) => toast(e.message, 'error'),
              })
            }
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
