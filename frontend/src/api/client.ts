const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api';

export class ApiError extends Error {
  status: number;
  code: string;
  fields: Record<string, string>;

  constructor(message: string, { status = 0, code = 'error', fields = {} }: { status?: number; code?: string; fields?: Record<string, string> } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
}

async function request<T>(path: string, { method = 'GET', body, signal }: RequestOptions = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (e: any) {
    if (e?.name === 'AbortError') throw e;
    throw new ApiError("We can't reach the server right now. Check your connection and try again.", {
      status: 0,
      code: 'network',
    });
  }
  if (res.status === 204) return null as T;
  let data: any = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON error page */
  }
  if (!res.ok) {
    const err = data?.error;
    const fallback =
      res.status >= 500
        ? 'Something went wrong on our side. Please try again in a moment.'
        : `Request failed (${res.status}).`;
    throw new ApiError(err?.message || fallback, {
      status: res.status,
      code: err?.code,
      fields: err?.fields || {},
    });
  }
  return data as T;
}

export const qs = (params: Record<string, any> = {}): string => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : '';
};

export const api = {
  get: <T = any>(path: string, opts?: RequestOptions): Promise<T> => request<T>(path, opts),
  post: <T = any>(path: string, body?: unknown): Promise<T> => request<T>(path, { method: 'POST', body: body ?? {} }),
  patch: <T = any>(path: string, body?: unknown): Promise<T> => request<T>(path, { method: 'PATCH', body }),
  put: <T = any>(path: string, body?: unknown): Promise<T> => request<T>(path, { method: 'PUT', body }),
  del: <T = any>(path: string): Promise<T> => request<T>(path, { method: 'DELETE' }),
};

