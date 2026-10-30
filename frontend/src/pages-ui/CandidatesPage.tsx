'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Checkbox,
  IconButton,
  InputAdornment,
  Link,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  TextField,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import SearchIcon from '@mui/icons-material/Search';
import SendIcon from '@mui/icons-material/Send';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import PeopleOutlineIcon from '@mui/icons-material/PeopleOutline';
import { Candidate, BatchDetail } from '../types';
import { useCandidates } from '../api/hooks';
import { useDebounced } from '../hooks';
import StatusChip from '../components/StatusChip';
import AddCandidateDialog from '../components/AddCandidateDialog';
import ConfirmDeleteDialog from '../components/ConfirmDeleteDialog';
import SendPanel from '../components/SendPanel';
import BulkResultDialog from '../components/BulkResultDialog';
import HistoryDrawer from '../components/HistoryDrawer';
import { EmptyState, ErrorState, RowSkeletons } from '../components/States';
import { useToast } from '../components/Toast';
import { formatDate, formatDateTime, formatPhone, getWhatsAppShareUrl, plural } from '../utils/format';

export default function CandidatesPage() {
  const toast = useToast();
  const [searchText, setSearchText] = useState('');
  const search = useDebounced(searchText.trim());
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [ordering, setOrdering] = useState('name');
  const [selected, setSelected] = useState<Map<string, Candidate>>(() => new Map());
  const [addOpen, setAddOpen] = useState(false);
  const [deleteTargets, setDeleteTargets] = useState<Candidate[]>([]);
  const [sendTargets, setSendTargets] = useState<Candidate[]>([]);
  const [sendKey, setSendKey] = useState(0);
  const [historyCandidate, setHistoryCandidate] = useState<Candidate | null>(null);
  const [batch, setBatch] = useState<{ id: string; initial: BatchDetail } | null>(null);

  useEffect(() => setPage(0), [search, rowsPerPage, ordering]);
  const { data, isPending, isError, error, refetch, isFetching } = useCandidates({
    search,
    ordering,
    page: page + 1,
    page_size: rowsPerPage,
  });
  const rows = data?.results ?? [];
  const total = data?.count ?? 0;

  useEffect(() => {
    if (data && rows.length === 0 && page > 0) setPage((p) => p - 1);
  }, [data]); // eslint-disable-line react-hooks/exhaustive-deps

  const allOnPage = rows.length > 0 && rows.every((r) => selected.has(r.id));
  const someOnPage = rows.some((r) => selected.has(r.id));
  const toggle = (c: Candidate) =>
    setSelected((s) => {
      const n = new Map(s);
      n.has(c.id) ? n.delete(c.id) : n.set(c.id, c);
      return n;
    });
  const togglePage = () =>
    setSelected((s) => {
      const n = new Map(s);
      if (allOnPage) rows.forEach((r) => n.delete(r.id));
      else rows.forEach((r) => n.set(r.id, r));
      return n;
    });

  const openSend = (list: Candidate[]) => {
    setSendTargets(list);
    setSendKey((k) => k + 1);
  };
  const chosen = useMemo(() => [...selected.values()], [selected]);
  const sortBy = (field: string) => setOrdering((o) => (o === field ? `-${field}` : field));
  const dir = (field: string): 'asc' | 'desc' | false =>
    ordering === field ? 'asc' : ordering === `-${field}` ? 'desc' : false;

  const handleSent = (
    result: any,
    { scheduled, when, recipients }: { scheduled: boolean; when?: string; recipients: Candidate[] }
  ) => {
    setSendTargets([]);
    setSelected(new Map());
    if (recipients.length === 1) {
      const r = result.results?.[0];
      if (r?.status === 'failed') toast(`${r.candidate.name}: ${r.failure_message}`, 'error');
      else if (scheduled) toast(`Message to ${r?.candidate?.name || 'candidate'} scheduled for ${formatDateTime(when)}.`);
      else toast(`Message to ${r?.candidate?.name || 'candidate'} is being sent.`, 'success');
    } else {
      setBatch({ id: result.batch_id, initial: result });
    }
  };

  const noCandidatesAtAll = !isPending && !isError && total === 0 && !search;
  const noMatches = !isPending && !isError && total === 0 && !!search;

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Candidate communication
      </Typography>
      <Paper variant="outlined">
        <Toolbar
          sx={{
            gap: 2,
            py: 2,
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            ...(selected.size > 0 && { bgcolor: '#e3f2fd' }),
          }}
        >
          {selected.size === 0 ? (
            <>
              <TextField
                size="small"
                placeholder="Search"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                sx={{ width: { xs: '100%', sm: 320 } }}
                slotProps={{
                  htmlInput: { 'aria-label': 'Search candidates by name, phone, email or ID' },
                  input: {
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon />
                      </InputAdornment>
                    ),
                  },
                }}
              />
              <Button variant="contained" startIcon={<AddIcon />} onClick={() => setAddOpen(true)}>
                Add Candidate
              </Button>
            </>
          ) : (
            <>
              <Typography variant="subtitle1" fontWeight={700}>
                {plural(selected.size, 'Candidate')} selected
              </Typography>
              <Stack direction="row" spacing={1}>
                <Button variant="contained" startIcon={<SendIcon />} onClick={() => openSend(chosen)}>
                  Send message
                </Button>
                <Button color="error" startIcon={<DeleteIcon />} onClick={() => setDeleteTargets(chosen)}>
                  Delete
                </Button>
                <Button onClick={() => setSelected(new Map())}>Clear</Button>
              </Stack>
            </>
          )}
        </Toolbar>

        <TableContainer>
          <Table aria-label="Candidates">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={someOnPage && !allOnPage}
                    checked={allOnPage}
                    onChange={togglePage}
                    inputProps={{ 'aria-label': 'Select all candidates on this page' }}
                  />
                </TableCell>
                <TableCell>Candidate ID</TableCell>
                <TableCell sortDirection={dir('name')}>
                  <TableSortLabel
                    active={!!dir('name')}
                    direction={dir('name') || 'asc'}
                    onClick={() => sortBy('name')}
                  >
                    Full name
                  </TableSortLabel>
                </TableCell>
                <TableCell sortDirection={dir('last_message_at')}>
                  <TableSortLabel
                    active={!!dir('last_message_at')}
                    direction={dir('last_message_at') || 'asc'}
                    onClick={() => sortBy('last_message_at')}
                  >
                    Last message
                  </TableSortLabel>
                </TableCell>
                <TableCell>Mobile number</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isPending && <RowSkeletons cols={7} />}
              {rows.map((c) => {
                const isSel = selected.has(c.id);
                return (
                  <TableRow
                    key={c.id}
                    hover
                    selected={isSel}
                    sx={{ '&:hover .row-actions': { opacity: 1 } }}
                  >
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={isSel}
                        onChange={() => toggle(c)}
                        inputProps={{ 'aria-label': `Select ${c.name}` }}
                      />
                    </TableCell>
                    <TableCell>{c.code}</TableCell>
                    <TableCell>
                      <Link
                        component="button"
                        type="button"
                        underline="hover"
                        color="text.primary"
                        onClick={() => setHistoryCandidate(c)}
                        sx={{ fontWeight: 600, textAlign: 'left', fontSize: 'inherit' }}
                      >
                        {c.name}
                      </Link>
                    </TableCell>
                    <TableCell>{formatDate(c.last_message_at)}</TableCell>
                    <TableCell>{formatPhone(c.phone)}</TableCell>
                    <TableCell>
                      <StatusChip status={c.last_message_status} />
                    </TableCell>
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      <Box
                        className="row-actions"
                        sx={{
                          opacity: { xs: 1, md: 0.55 },
                          transition: 'opacity .15s',
                          '&:focus-within': { opacity: 1 },
                        }}
                      >
                        <Tooltip title={`Send message to ${c.name}`}>
                          <IconButton
                            aria-label={`Send message to ${c.name}`}
                            size="small"
                            onClick={() => openSend([c])}
                          >
                            <SendIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        {c.phone && (
                          <Tooltip title={`Share on WhatsApp with ${c.name}`}>
                            <IconButton
                              aria-label={`Share on WhatsApp with ${c.name}`}
                              size="small"
                              color="success"
                              onClick={() =>
                                window.open(
                                  getWhatsAppShareUrl(c.phone, `Hello ${c.name}, `),
                                  '_blank',
                                  'noopener,noreferrer'
                                )
                              }
                            >
                              <WhatsAppIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        <Tooltip title={`Delete ${c.name}`}>
                          <IconButton
                            aria-label={`Delete ${c.name}`}
                            size="small"
                            onClick={() => setDeleteTargets([c])}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>

        {isError && <ErrorState error={error} onRetry={refetch} title="Couldn't load candidates" />}
        {noCandidatesAtAll && (
          <EmptyState
            icon={<PeopleOutlineIcon color="disabled" sx={{ fontSize: 56 }} />}
            title="No candidates added"
            description="When you add a candidate, they will appear here."
            action={
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => setAddOpen(true)}
                sx={{ mt: 1 }}
              >
                Add Candidate
              </Button>
            }
          />
        )}
        {noMatches && (
          <EmptyState
            title={`No candidates match “${search}”`}
            description="Check the spelling, or search by name, phone number, email or candidate ID."
            action={<Button onClick={() => setSearchText('')}>Clear search</Button>}
          />
        )}

        <TablePagination
          component="div"
          count={total}
          page={Math.min(page, Math.max(0, Math.ceil(total / rowsPerPage) - 1))}
          rowsPerPage={rowsPerPage}
          rowsPerPageOptions={[10, 25, 50]}
          onPageChange={(_, p) => setPage(p)}
          onRowsPerPageChange={(e) => setRowsPerPage(Number(e.target.value))}
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} of ${count}`}
          sx={{ opacity: isFetching && !isPending ? 0.7 : 1 }}
        />
      </Paper>

      <AddCandidateDialog open={addOpen} onClose={() => setAddOpen(false)} />
      <ConfirmDeleteDialog
        candidates={deleteTargets}
        onClose={() => setDeleteTargets([])}
        onDeleted={(gone) => {
          setSelected((s) => {
            const n = new Map(s);
            gone.forEach((g) => n.delete(g.id));
            return n;
          });
          if (historyCandidate && gone.some((g) => g.id === historyCandidate.id))
            setHistoryCandidate(null);
        }}
      />
      {sendTargets.length > 0 && (
        <SendPanel
          key={sendKey}
          open
          recipients={sendTargets}
          onClose={() => setSendTargets([])}
          onSent={handleSent}
        />
      )}
      {batch && (
        <BulkResultDialog
          batchId={batch.id}
          initial={batch.initial}
          onClose={() => setBatch(null)}
        />
      )}
      <HistoryDrawer
        candidate={historyCandidate}
        onClose={() => setHistoryCandidate(null)}
        onSend={(c) => {
          setHistoryCandidate(null);
          openSend([c]);
        }}
      />
    </Box>
  );
}

