'use client';

import React from 'react';
import { AppBar, Alert, Box, Container, Stack, Tab, Tabs, Toolbar, Typography } from '@mui/material';
import ForumOutlinedIcon from '@mui/icons-material/ForumOutlined';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import HealthChip from './HealthChip';
import { useHealth } from '../api/hooks';

const TABS = [
  { to: '/', label: 'Candidates' },
  { to: '/activity', label: 'Activity' },
  { to: '/templates', label: 'Templates' },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const current = TABS.find((t) => t.to !== '/' && pathname.startsWith(t.to))?.to ?? '/';
  const { data: health, isError } = useHealth();

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'grey.100' }}>
      <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Toolbar sx={{ gap: 3, flexWrap: 'wrap' }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ color: 'primary.main' }}>
            <ForumOutlinedIcon />
            <Typography
              variant="h6"
              sx={{ color: 'text.primary', display: { xs: 'none', md: 'block' }, fontWeight: 700 }}
            >
              Candidate Communication
            </Typography>
          </Stack>
          <Tabs value={current} sx={{ flexGrow: 1 }} aria-label="Main navigation">
            {TABS.map((t) => (
              <Tab key={t.to} value={t.to} label={t.label} component={Link} href={t.to} />
            ))}
          </Tabs>
          <HealthChip />
        </Toolbar>
      </AppBar>

      {isError && (
        <Alert severity="error" square>
          The platform can't be reached. Check that the server is running — anything you see may be out of date.
        </Alert>
      )}
      {health?.status === 'outage' && (
        <Alert severity="warning" square>
          The communication service is currently unavailable. Messages you send now will wait in the queue and go out automatically when it's back.
        </Alert>
      )}
      {health && !health.worker_running && (
        <Alert severity="warning" square>
          Message processing is paused (the background worker isn't running). Messages will stay queued until it's started.
        </Alert>
      )}

      <Container maxWidth="xl" sx={{ py: 3 }}>
        {children}
      </Container>
    </Box>
  );
}

