'use client';

import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  InputAdornment,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import InboxOutlinedIcon from '@mui/icons-material/InboxOutlined';
import { useCancelMessage, useMessages, useRetryMessages } from '../api/hooks';
import { useDebounced } from '../hooks';
import StatusChip from '../components/StatusChip';
import { EmptyState, ErrorState, RowSkeletons } from '../components/States';
import { useToast } from '../components/Toast';
import { formatDateTime } from '../utils/format';

const FILTERS = [
  ['', 'All'],
  ['scheduled', 'Scheduled'],
  ['queued,sending', 'Queued'],
  ['sent', 'Sent'],
  ['delivered', 'Delivered'],
  ['read', 'Read'],
  ['failed', 'Failed'],
];

export default function ActivityPage() {
  const toast = useToast();
  const [filter, setFilter] = useState('');
  const [text, setText] = useState('');
  const search = useDebounced(text.trim());
  const [page, setPage] = useState(0);
  const [rows, setRows] = useState(10);

  useEffect(() => setPage(0), [filter, search, rows]);

  const { data, isPending, isError, error, refetch } = useMessages({
    status: filter || undefined,
    search,
    page: page + 1,
    page_size: rows,
    ordering: filter === 'scheduled' ? 'scheduled_at' : undefined,
  });

  const retry = useRetryMessages();
  const cancel = useCancelMessage();
  const list = (data?.results as any[]) ?? [];

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Message activity
      </Typography>
      <Paper variant="outlined">
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          spacing={2}
          sx={{ p: 2 }}
          justifyContent="space-between"
        >
          <Stack
            direction="row"
            spacing={1}
            flexWrap="wrap"
            useFlexGap
            role="group"
            aria-label="Filter by status"
          >
            {FILTERS.map(([v, l]) => (
              <Chip
                key={l}
                label={l}
                clickable
                color={filter === v ? 'primary' : 'default'}
                variant={filter === v ? 'filled' : 'outlined'}
                onClick={() => setFilter(v)}
              />
            ))}
          </Stack>
          <TextField
            size="small"
            placeholder="Search candidate or text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            sx={{ width: { xs: '100%', md: 300 } }}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              },
            }}
          />
        </Stack>
        <TableContainer>
          <Table sx={{ minWidth: 800 }} aria-label="Message activity">
            <TableHead>
              <TableRow>
                <TableCell>Candidate</TableCell>
                <TableCell>Message</TableCell>
                <TableCell>Channel</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>When</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isPending && <RowSkeletons cols={6} />}
              {list.map((m: any) => (
                <TableRow key={m.id} hover>
                  <TableCell sx={{ fontWeight: 600 }}>{m.candidate?.name || m.candidate_name}</TableCell>
                  <TableCell sx={{ maxWidth: 360 }}>
                    <Typography variant="body2" noWrap title={m.body}>
                      {m.body}
                    </Typography>
                    {m.failure_message && (
                      <Typography
                        variant="caption"
                        color={m.status === 'failed' ? 'error' : 'text.secondary'}
                        display="block"
                      >
                        {m.failure_message}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>{m.channel_label}</TableCell>
                  <TableCell>
                    <StatusChip status={m.status} />
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {m.status === 'scheduled'
                      ? `Sends ${formatDateTime(m.scheduled_at)}`
                      : formatDateTime(m.created_at)}
                  </TableCell>
                  <TableCell align="right">
                    {m.can_retry && (
                      <Button
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
                    )}
                    {m.status === 'failed' && !m.can_retry && (
                      <Tooltip title="This failure is permanent. Fix the candidate's details and send a new message.">
                        <span>
                          <Button size="small" disabled>
                            Can't retry
                          </Button>
                        </span>
                      </Tooltip>
                    )}
                    {m.can_cancel && (
                      <Button
                        size="small"
                        color="error"
                        disabled={cancel.isPending}
                        onClick={() =>
                          cancel.mutate(m.id, {
                            onSuccess: () => toast('Scheduled message cancelled.', 'info'),
                            onError: (e: any) => toast(e.message, 'error'),
                          })
                        }
                      >
                        Cancel
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        {isError && <ErrorState error={error} onRetry={refetch} title="Couldn't load activity" />}
        {!isPending && !isError && list.length === 0 && (
          <EmptyState
            icon={<InboxOutlinedIcon color="disabled" sx={{ fontSize: 56 }} />}
            title={filter || search ? 'Nothing matches these filters' : 'No messages yet'}
            description={
              filter || search
                ? 'Try a different status or clear the search.'
                : 'Messages you send or schedule will show up here.'
            }
          />
        )}
        <TablePagination
          component="div"
          count={data?.count ?? 0}
          page={page}
          rowsPerPage={rows}
          rowsPerPageOptions={[10, 25, 50]}
          onPageChange={(_, p) => setPage(p)}
          onRowsPerPageChange={(e) => setRows(Number(e.target.value))}
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} of ${count}`}
        />
      </Paper>
    </Box>
  );
}

