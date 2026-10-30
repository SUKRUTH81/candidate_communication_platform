'use client';

import React, { useState } from 'react';
import { Box, Chip, Divider, Popover, Stack, Typography } from '@mui/material';
import { useHealth } from '../api/hooks';

const META: Record<string, { label: string; color: string }> = {
  operational: { label: 'Operational', color: 'success.main' },
  degraded: { label: 'Degraded', color: 'warning.main' },
  outage: { label: 'Unavailable', color: 'error.main' },
};

function Dot({ color }: { color: string }) {
  return (
    <Box
      component="span"
      sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: color, display: 'inline-block' }}
    />
  );
}

export default function HealthChip() {
  const { data, isError } = useHealth();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const status = isError ? 'outage' : data?.status;
  const meta = (status && META[status]) || { label: 'Checking…', color: 'grey.400' };
  const t = data?.totals;

  return (
    <>
      <Chip
        variant="outlined"
        clickable
        onClick={(e) => setAnchor(e.currentTarget)}
        icon={<Dot color={meta.color} />}
        label={`Communication service: ${meta.label}`}
        aria-label={`Communication service status: ${meta.label}. Click for details`}
        sx={{ '& .MuiChip-icon': { ml: 1.25 }, display: { xs: 'none', sm: 'inline-flex' } }}
      />
      <Chip
        variant="outlined"
        clickable
        onClick={(e) => setAnchor(e.currentTarget)}
        icon={<Dot color={meta.color} />}
        label={meta.label}
        sx={{ '& .MuiChip-icon': { ml: 1.25 }, display: { xs: 'inline-flex', sm: 'none' } }}
      />
      <Popover
        open={!!anchor}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Stack spacing={1.5} sx={{ p: 2.5, minWidth: 290 }}>
          <Typography variant="subtitle2" color="text.secondary">
            Communication Service
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            <Dot color={meta.color} />
            <Typography fontWeight={700}>{meta.label}</Typography>
          </Stack>
          {isError && (
            <Typography variant="body2" color="error">
              The platform API can't be reached.
            </Typography>
          )}
          {t && (
            <>
              <Divider />
              {[
                ['Messages Sent', t.sent],
                ['Messages Delivered', t.delivered],
                ['Messages Read', t.read],
                ['Messages Failed', t.failed],
                ['In queue', t.pending],
                ['Scheduled', t.scheduled],
              ].map(([k, v]) => (
                <Stack key={k as string} direction="row" justifyContent="space-between">
                  <Typography variant="body2">{k}</Typography>
                  <Typography variant="body2" fontWeight={700}>
                    {v}
                  </Typography>
                </Stack>
              ))}
              <Divider />
              {data?.providers?.map((p) => (
                <Stack key={p.name} direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2">{p.name}</Typography>
                  <Stack direction="row" spacing={0.75} alignItems="center">
                    <Dot color={p.operational ? 'success.main' : 'error.main'} />
                    <Typography variant="caption">{p.channels.join(', ')}</Typography>
                  </Stack>
                </Stack>
              ))}
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2">Background worker</Typography>
                <Typography
                  variant="body2"
                  color={data?.worker_running ? 'success.main' : 'error.main'}
                  fontWeight={700}
                >
                  {data?.worker_running ? 'Running' : 'Stopped'}
                </Typography>
              </Stack>
            </>
          )}
        </Stack>
      </Popover>
    </>
  );
}

