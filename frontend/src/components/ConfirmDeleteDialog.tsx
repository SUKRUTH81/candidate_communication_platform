'use client';

import React from 'react';
import {
  Alert,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material';
import { Candidate } from '../types';
import { useDeleteCandidates } from '../api/hooks';
import { useToast } from './Toast';

interface ConfirmDeleteDialogProps {
  candidates: Candidate[];
  onClose: () => void;
  onDeleted?: (deletedCandidates: Candidate[]) => void;
}

export default function ConfirmDeleteDialog({
  candidates,
  onClose,
  onDeleted,
}: ConfirmDeleteDialogProps) {
  const del = useDeleteCandidates();
  const toast = useToast();
  const open = candidates.length > 0;
  const single = candidates.length === 1;

  const close = () => {
    if (!del.isPending) {
      del.reset();
      onClose();
    }
  };

  const confirm = () =>
    del.mutate(
      candidates.map((c) => c.id),
      {
        onSuccess: (r) => {
          toast(r.deleted === 1 ? 'Candidate deleted.' : `${r.deleted} candidates deleted.`);
          onDeleted?.(candidates);
          onClose();
        },
      }
    );

  return (
    <Dialog open={open} onClose={close} maxWidth="xs" fullWidth aria-labelledby="delete-title">
      <DialogTitle id="delete-title" sx={{ fontWeight: 700 }}>
        {single
          ? 'Are you sure you want to delete this Candidate?'
          : `Are you sure you want to delete ${candidates.length} Candidates?`}
      </DialogTitle>
      <DialogContent>
        <DialogContentText>
          {single ? (
            <>
              This action cannot be undone, and you’ll lose all communication history with{' '}
              <strong>{candidates[0]?.name}</strong>.
            </>
          ) : (
            'This action cannot be undone, and you’ll lose all communication history with these candidates.'
          )}
        </DialogContentText>
        {del.isError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {(del.error as any)?.message || 'Failed to delete.'}
          </Alert>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={close} disabled={del.isPending}>
          Cancel
        </Button>
        <Button
          color="error"
          variant="contained"
          onClick={confirm}
          disabled={del.isPending}
          startIcon={del.isPending ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {del.isPending ? 'Deleting…' : 'Delete Candidate'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

