'use client';

import React from 'react';
import { Chip, CircularProgress, Tooltip } from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import DoneAllIcon from '@mui/icons-material/DoneAll';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import ScheduleIcon from '@mui/icons-material/Schedule';
import SendIcon from '@mui/icons-material/Send';
import BlockIcon from '@mui/icons-material/Block';
import { MessageStatus } from '../types';
import { STATUS } from '../utils/status';

const ICONS: Record<MessageStatus, React.ReactElement> = {
  scheduled: <ScheduleIcon />,
  queued: <ScheduleIcon />,
  sending: <CircularProgress size={12} thickness={6} color="inherit" />,
  sent: <SendIcon />,
  delivered: <CheckIcon />,
  read: <DoneAllIcon />,
  failed: <ErrorOutlineIcon />,
  cancelled: <BlockIcon />,
};

interface StatusChipProps {
  status?: MessageStatus | null;
  tooltip?: string;
  size?: 'small' | 'medium';
}

export default function StatusChip({ status, tooltip, size = 'small' }: StatusChipProps) {
  if (!status) return <span aria-label="No status">NA</span>;
  const meta = STATUS[status] || { label: status, color: 'default', variant: 'outlined' };
  const chip = (
    <Chip
      size={size}
      label={meta.label}
      color={meta.color as any}
      variant={meta.variant}
      icon={ICONS[status]}
      data-status={status}
      sx={{ '& .MuiChip-icon': { fontSize: 16 }, ...(status === 'sent' && { color: '#fff' }) }}
    />
  );
  return tooltip ? <Tooltip title={tooltip}>{chip}</Tooltip> : chip;
}

