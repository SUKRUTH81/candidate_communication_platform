'use client';

import React, { useState } from 'react';
import {
  Alert,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
} from '@mui/material';
import { useCreateCandidate } from '../api/hooks';
import { useToast } from './Toast';

const EMPTY = { name: '', phone: '', email: '' };

function validate(v: typeof EMPTY) {
  const e: Record<string, string> = {};
  if (v.name.trim().length < 2) e.name = 'Enter the candidate’s full name.';
  if (!v.phone.trim()) e.phone = 'Enter a mobile number.';
  else if (v.phone.replace(/\D/g, '').length < 8) e.phone = 'This number looks too short.';
  if (v.email.trim() && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v.email.trim()))
    e.email = 'Enter a valid email address.';
  return e;
}

interface AddCandidateDialogProps {
  open: boolean;
  onClose: () => void;
}

export default function AddCandidateDialog({ open, onClose }: AddCandidateDialogProps) {
  const [values, setValues] = useState(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState('');
  const create = useCreateCandidate();
  const toast = useToast();

  const close = () => {
    if (create.isPending) return;
    setValues(EMPTY);
    setErrors({});
    setFormError('');
    onClose();
  };

  const set = (k: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setValues((v) => ({ ...v, [k]: e.target.value }));
    setErrors((er) => ({ ...er, [k]: undefined as any }));
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const local = validate(values);
    setErrors(local);
    if (Object.keys(local).length) return;
    setFormError('');
    create.mutate(
      { name: values.name.trim(), phone: values.phone.trim(), email: values.email.trim() },
      {
        onSuccess: (c) => {
          toast(`${c.name} was added.`);
          setValues(EMPTY);
          setErrors({});
          onClose();
        },
        onError: (err: any) => {
          if (err.fields && Object.keys(err.fields).length) setErrors(err.fields);
          else setFormError(err.message || 'Failed to add candidate.');
        },
      }
    );
  };

  return (
    <Dialog open={open} onClose={close} fullWidth maxWidth="xs" PaperProps={{ component: 'form', onSubmit: submit } as any}>
      <DialogTitle sx={{ fontWeight: 700 }}>Add candidate</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          {formError && <Alert severity="error">{formError}</Alert>}
          <TextField
            label="Full name"
            required
            autoFocus
            value={values.name}
            onChange={set('name')}
            error={!!errors.name}
            helperText={errors.name}
            disabled={create.isPending}
          />
          <TextField
            label="Mobile number"
            required
            value={values.phone}
            onChange={set('phone')}
            error={!!errors.phone}
            helperText={errors.phone || 'Indian numbers work as-is. Add country code (+91…) if needed.'}
            disabled={create.isPending}
            slotProps={{ htmlInput: { inputMode: 'tel' } }}
          />
          <TextField
            label="Email"
            type="email"
            value={values.email}
            onChange={set('email')}
            error={!!errors.email}
            helperText={errors.email || 'Optional — needed to send emails.'}
            disabled={create.isPending}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={close} disabled={create.isPending}>
          Cancel
        </Button>
        <Button
          type="submit"
          variant="contained"
          disabled={create.isPending}
          startIcon={create.isPending ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {create.isPending ? 'Adding…' : 'Add candidate'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
