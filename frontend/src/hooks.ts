'use client';

import { useEffect, useState } from 'react';

export function useDebounced<T>(value: T, delay: number = 300): T {
  const [v, setV] = useState<T>(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}

