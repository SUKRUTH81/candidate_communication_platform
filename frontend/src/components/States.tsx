'use client';

import React from 'react';
import { Alert, Box, Button, Skeleton, Stack, Typography } from '@mui/material';

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}

export function EmptyState({ title, description, action, icon }: EmptyStateProps) {
  return (
    <Stack alignItems="center" spacing={1} sx={{ py: 10, px: 2, textAlign: 'center' }} role="status">
      {icon}
      <Typography variant="h6">{title}</Typography>
      {description && <Typography color="text.secondary" sx={{ maxWidth: 420 }}>{description}</Typography>}
      {action}
    </Stack>
  );
}

interface ErrorStateProps {
  error?: any;
  onRetry?: () => void;
  title?: string;
}

export function ErrorState({ error, onRetry, title = "Couldn't load this" }: ErrorStateProps) {
  return (
    <Box sx={{ p: 3 }}>
      <Alert
        severity="error"
        action={
          onRetry && (
            <Button color="inherit" size="small" onClick={onRetry}>
              Try again
            </Button>
          )
        }
      >
        <strong>{title}.</strong> {error?.message || 'Something went wrong.'}
      </Alert>
    </Box>
  );
}

export function RowSkeletons({ rows = 6, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, r) => (
        <tr key={r} aria-hidden>
          {Array.from({ length: cols }).map((__, c) => (
            <td key={c} style={{ padding: '14px 16px' }}>
              <Skeleton variant="text" width={c === 0 ? 24 : '70%'} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

