'use client';

import React, { useLayoutEffect, useRef, useState } from 'react';
import { Box, Chip, Tooltip } from '@mui/material';
import { Candidate } from '../types';

const GAP = 8;
const MAX_LINES = 2;

export function countVisible(widths: number[], containerWidth: number, plusWidth: number): number {
  const place = (list: number[]) => {
    let row = 0;
    let x = 0;
    let placed = 0;
    for (const w of list) {
      let nx = x === 0 ? w : x + GAP + w;
      let nr = row;
      if (nx > containerWidth && x !== 0) {
        nr += 1;
        nx = w;
      }
      if (nr >= MAX_LINES) break;
      row = nr;
      x = nx;
      placed += 1;
    }
    return { placed, row, x };
  };

  if (place(widths).placed === widths.length) return widths.length;
  let row = 0;
  let x = 0;
  let count = 0;
  for (let i = 0; i < widths.length; i += 1) {
    let nx = x === 0 ? widths[i] : x + GAP + widths[i];
    let nr = row;
    if (nx > containerWidth && x !== 0) {
      nr += 1;
      nx = widths[i];
    }
    if (nr >= MAX_LINES) break;
    const plusFitsSameLine = nx + GAP + plusWidth <= containerWidth;
    if (!plusFitsSameLine && nr === MAX_LINES - 1) break;
    row = nr;
    x = nx;
    count = i + 1;
  }
  return Math.max(count, 0);
}

interface RecipientChipsProps {
  recipients: Candidate[];
  onRemove?: (c: Candidate) => void;
}

export default function RecipientChips({ recipients, onRemove }: RecipientChipsProps) {
  const boxRef = useRef<HTMLDivElement>(null);
  const ghostRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [visible, setVisible] = useState(recipients.length);
  const removable = !!onRemove && recipients.length > 1;
  const key = `${recipients.map((r) => r.id).join(',')}|${removable}`;

  useLayoutEffect(() => {
    const el = boxRef.current;
    if (!el) return undefined;
    setWidth(el.clientWidth);
    if (typeof ResizeObserver === 'undefined') return undefined;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useLayoutEffect(() => {
    const ghost = ghostRef.current;
    if (!ghost || !width) return;
    const widths = [...ghost.children].map((c) => (c as HTMLElement).offsetWidth);
    const plusWidth = widths.pop() || 56;
    setVisible(countVisible(widths, width, plusWidth));
  }, [key, width]);

  const shown = recipients.slice(0, visible);
  const hidden = recipients.slice(visible);
  const chip = (r: Candidate, extra: any = {}, chipKey = r.id) => (
    <Chip
      key={chipKey}
      label={r.name}
      onDelete={removable ? () => onRemove?.(r) : undefined}
      sx={{ maxWidth: 180, flexShrink: 0 }}
      {...extra}
    />
  );

  return (
    <>
      <Box
        ref={boxRef}
        sx={{ display: 'flex', flexWrap: 'wrap', gap: `${GAP}px`, maxHeight: 72, overflow: 'hidden' }}
        aria-label="Recipients"
      >
        {shown.map((r) => chip(r))}
        {hidden.length > 0 && (
          <Tooltip title={hidden.slice(0, 15).map((h) => h.name).join(', ') + (hidden.length > 15 ? '…' : '')}>
            <Chip
              label={`+${hidden.length}`}
              color="primary"
              variant="outlined"
              data-testid="more-recipients"
            />
          </Tooltip>
        )}
      </Box>
      <Box
        ref={ghostRef}
        aria-hidden
        sx={{
          position: 'absolute',
          visibility: 'hidden',
          pointerEvents: 'none',
          display: 'flex',
          gap: `${GAP}px`,
          height: 0,
          overflow: 'hidden',
          whiteSpace: 'nowrap',
        }}
      >
        {recipients.map((r) => chip(r, { tabIndex: -1 }, `g-${r.id}`))}
        <Chip label={`+${Math.max(recipients.length, 10)}`} variant="outlined" sx={{ flexShrink: 0 }} />
      </Box>
    </>
  );
}

